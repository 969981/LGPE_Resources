#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--update-existing" ) ]]; then
  printf 'Usage: %s [--update-existing]\n' "$0" >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(cd -- "$script_dir/.." && pwd)
dest="$root/tools/src"
update_existing=0
if [[ ${1:-} == "--update-existing" ]]; then update_existing=1; fi
mkdir -p "$dest"

repos=(
  'pkNX|https://github.com/kwsch/pkNX.git'
  'Pawn|https://github.com/compuphase/pawn.git'
  'Switch-Toolbox|https://github.com/KillzXGaming/Switch-Toolbox.git'
  'pokedat|https://github.com/Digote/pokedat.git'
  'read_swsh|https://github.com/CMahk/read_swsh.git'
  'io_scene_gfbanm|https://github.com/Shararamosh/io_scene_gfbanm.git'
  'Pokemon-Switch-Model-Importer-Blender|https://github.com/ChicoEevee/Pokemon-Switch-Model-Importer-Blender.git'
  'vgmstream|https://github.com/vgmstream/vgmstream.git'
  'wwiser|https://github.com/bnnm/wwiser.git'
  'Ghidra-Switch-Loader|https://github.com/Adubbz/Ghidra-Switch-Loader.git'
  'BNTX-Extractor|https://github.com/aboood40091/BNTX-Extractor.git'
  'pokeldn|https://github.com/Decryptu/pokeldn.git'
  'pbseqtool|https://github.com/lincoln-lm/pbseqtool.git'
)
declare -A pinned_commits=(
  [pokeldn]=0afe6f61f25464767e55b909eef6b260a372bb34
  [pbseqtool]=6f122d1b7945797cae472960b798bf28523f8acd
)

for entry in "${repos[@]}"; do
  name=${entry%%|*}
  remote=${entry#*|}
  path="$dest/$name"
  if [[ ! -d "$path/.git" ]]; then
    git clone --depth 1 "$remote" "$path"
  elif (( update_existing )) && [[ -z ${pinned_commits[$name]:-} ]]; then
    git -C "$path" pull --ff-only
  fi
done

for name in "${!pinned_commits[@]}"; do
  path="$dest/$name"
  if [[ -d "$path/.git" ]]; then
    current_commit=$(git -C "$path" rev-parse HEAD)
    if [[ "$current_commit" != "${pinned_commits[$name]}" ]]; then
      git -C "$path" fetch --depth 1 origin "${pinned_commits[$name]}"
      git -C "$path" checkout --detach "${pinned_commits[$name]}"
    fi
  fi
done

provenance="$root/tools/source-revisions.tsv"
temporary="$provenance.partial"
trap 'rm -f "$temporary"' EXIT
printf 'name\tcommit\tremote\n' > "$temporary"
for entry in "${repos[@]}"; do
  name=${entry%%|*}
  expected_remote=${entry#*|}
  path="$dest/$name"
  if [[ -d "$path/.git" ]]; then
    commit=$(git -C "$path" rev-parse HEAD)
    remote=$(git -C "$path" remote get-url origin)
    if [[ "${remote%.git}" != "${expected_remote%.git}" ]]; then
      printf 'Remote mismatch for %s: expected %s, found %s\n' "$name" "$expected_remote" "$remote" >&2
      exit 3
    fi
    printf '%s\t%s\t%s\n' "$name" "$commit" "$expected_remote" >> "$temporary"
  fi
done
mv "$temporary" "$provenance"
trap - EXIT
printf 'Pinned source revision list: %s\n' "$provenance"
