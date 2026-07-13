#!/bin/zsh
set -euo pipefail

config_path="${MLX_WHISPER_CONFIG:-$HOME/.config/georgeskills/mlx-whisper.env}"
if [[ -f "$config_path" ]]; then
  source "$config_path"
fi

: "${MLX_WHISPER_RUNTIME:?Set MLX_WHISPER_RUNTIME in $config_path or the environment}"
: "${HF_HOME:?Set HF_HOME in $config_path or the environment}"

runtime_python="$MLX_WHISPER_RUNTIME/venv/bin/python"
script_dir="${0:A:h}"

if [[ ! -x "$runtime_python" ]]; then
  print -u2 "MLX Whisper runtime is missing: $runtime_python"
  exit 2
fi
if [[ ! -d "$HF_HOME" ]]; then
  print -u2 "Hugging Face cache is unavailable: $HF_HOME"
  exit 2
fi

"$runtime_python" -c \
  "import platform, mlx, mlx_whisper; assert platform.machine() == 'arm64', platform.machine(); print('MLX runtime: native arm64', mlx_whisper.__version__)"

export HF_HOME
exec "$runtime_python" "$script_dir/mlx_transcriber.py" "$@"
