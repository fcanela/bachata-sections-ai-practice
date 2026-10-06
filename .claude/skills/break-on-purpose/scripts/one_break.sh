#!/usr/bin/env bash
# One break: run the checks on the broken code, then write the files back as committed.
#
#   one_break.sh <name> <file>... -- <command that runs the checks>
#       The files are already broken, by hand. The break is kept as a patch under <name>.
#
#   one_break.sh <name> -- <command that runs the checks>
#       Applies the patch kept under <name> first, so the very same break runs again.
#
# Run it from the root of the repository. It refuses to run when a named file does not
# differ from the commit: the break did not apply, and a passing run would say nothing.
# The files are written back when the command ends, however it ends. Its exit status is
# the command's. Patches are kept in the repository's git folder, under breaks/, where
# git does not list them.

set -u

name="${1:?usage: one_break.sh <name> [<file>...] -- <command>}"
shift
files=()
while [ $# -gt 0 ] && [ "$1" != "--" ]; do
  files+=("$1")
  shift
done
if [ "${1:-}" != "--" ] || [ $# -lt 2 ]; then
  echo "one_break: put -- and the command that runs the checks after the files" >&2
  exit 2
fi
shift

kept="$(git rev-parse --git-dir)/breaks"
patch="$kept/$name.patch"
mkdir -p "$kept"

if [ ${#files[@]} -eq 0 ]; then
  if [ ! -s "$patch" ]; then
    echo "one_break: no break is kept as $name" >&2
    exit 2
  fi
  mapfile -t files < <(git apply --numstat "$patch" | cut -f3)
  if ! git diff --quiet HEAD -- "${files[@]}"; then
    echo "one_break: ${files[*]} already differ from the commit; write them back first" >&2
    exit 2
  fi
  git apply "$patch" || exit 2
else
  for file in "${files[@]}"; do
    if git diff --quiet HEAD -- "$file"; then
      echo "one_break: $file is as committed, so the break did not apply" >&2
      exit 2
    fi
  done
  git diff HEAD -- "${files[@]}" > "$patch"
fi

restore() {
  git checkout -q HEAD -- "${files[@]}" && echo "written back: ${files[*]}"
}
trap restore EXIT
trap 'exit 130' INT TERM HUP

echo "break: $name,$(git diff --shortstat HEAD -- "${files[@]}")"
start=$SECONDS
"$@"
status=$?
echo "checks: exit $status after $((SECONDS - start)) s"
exit $status
