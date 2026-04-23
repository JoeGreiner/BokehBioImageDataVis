import ffmpeg
from typing import Any, Dict, List, Optional

H264_PRESETS = (
    'ultrafast',
    'superfast',
    'veryfast',
    'faster',
    'fast',
    'medium',
    'slow',
    'slower',
    'veryslow',
)
AV1_PRESETS = tuple(range(13))

_ENCODING_DEFAULTS = {
    'h264': {
        'vcodec': 'libx264',
        'crf': 19,
        'preset': 'veryfast',
        'pix_fmt': 'yuv420p',
    },
    'av1': {
        'vcodec': 'libsvtav1',
        'crf': 36,
        'preset': 5,
        'pix_fmt': 'yuv420p',
    },
}


def _validate_encoding(encoding: str) -> None:
    if encoding not in _ENCODING_DEFAULTS:
        raise ValueError(f'Unknown encoding: {encoding}')


def _validate_ffmpeg_options(ffmpeg_options: Optional[Dict[str, Any]]) -> None:
    if ffmpeg_options is None:
        return
    if not isinstance(ffmpeg_options, dict):
        raise TypeError(f'ffmpeg_options must be a dict or None, got {type(ffmpeg_options).__name__}')


def validate_preset(encoding: str, preset: Any) -> None:
    _validate_encoding(encoding)

    if encoding == 'h264' and preset not in H264_PRESETS:
        raise ValueError(
            'ffmpeg_preset must be one of ultrafast, superfast, veryfast, faster, fast, '
            f'medium, slow, slower, veryslow, got {preset}'
        )
    if encoding == 'av1' and preset not in AV1_PRESETS:
        raise ValueError(
            'ffmpeg_preset must be one of 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, '
            f'got {preset}'
        )


def resolve_ffmpeg_output_kwargs(encoding: str,
                                 *,
                                 ffmpeg_crf: Optional[int] = None,
                                 ffmpeg_preset: Optional[Any] = None,
                                 ffmpeg_options: Optional[Dict[str, Any]] = None,
                                 default_crf: Optional[int] = None,
                                 default_preset: Optional[Any] = None,
                                 extra_output_kwargs: Optional[Dict[str, Any]] = None,
                                 ) -> Dict[str, Any]:
    _validate_encoding(encoding)
    _validate_ffmpeg_options(ffmpeg_options)

    output_kwargs = dict(_ENCODING_DEFAULTS[encoding])

    if default_crf is not None:
        output_kwargs['crf'] = default_crf
    if default_preset is not None:
        output_kwargs['preset'] = default_preset
    if extra_output_kwargs is not None:
        output_kwargs.update(extra_output_kwargs)
    if ffmpeg_crf is not None:
        output_kwargs['crf'] = ffmpeg_crf
    if ffmpeg_preset is not None:
        output_kwargs['preset'] = ffmpeg_preset
    if ffmpeg_options is not None:
        output_kwargs.update(ffmpeg_options)

    if 'preset' in output_kwargs:
        validate_preset(encoding, output_kwargs['preset'])

    return output_kwargs


def build_ffmpeg_output_stream(input_stream,
                               output_path: str,
                               encoding: str,
                               *,
                               ffmpeg_crf: Optional[int] = None,
                               ffmpeg_preset: Optional[Any] = None,
                               ffmpeg_options: Optional[Dict[str, Any]] = None,
                               default_crf: Optional[int] = None,
                               default_preset: Optional[Any] = None,
                               extra_output_kwargs: Optional[Dict[str, Any]] = None,
                               ):
    output_kwargs = resolve_ffmpeg_output_kwargs(
        encoding,
        ffmpeg_crf=ffmpeg_crf,
        ffmpeg_preset=ffmpeg_preset,
        ffmpeg_options=ffmpeg_options,
        default_crf=default_crf,
        default_preset=default_preset,
        extra_output_kwargs=extra_output_kwargs,
    )
    return ffmpeg.output(input_stream, output_path, **output_kwargs)


def _convert_ffmpeg_output_kwargs_to_cli_args(output_kwargs: Dict[str, Any]) -> List[str]:
    args: List[str] = []
    for key, value in output_kwargs.items():
        if value is False:
            continue

        flag = f'-{key}'
        if value is None or value is True:
            args.append(flag)
            continue

        args.extend([flag, str(value)])

    return args


def build_ffmpeg_subprocess_args(*,
                                 input_args: List[str],
                                 output_path: str,
                                 encoding: str,
                                 ffmpeg_crf: Optional[int] = None,
                                 ffmpeg_preset: Optional[Any] = None,
                                 ffmpeg_options: Optional[Dict[str, Any]] = None,
                                 default_crf: Optional[int] = None,
                                 default_preset: Optional[Any] = None,
                                 extra_output_kwargs: Optional[Dict[str, Any]] = None,
                                 global_args: Optional[List[str]] = None,
                                 overwrite_output: bool = True,
                                 ) -> List[str]:
    if not isinstance(input_args, list) or not all(isinstance(arg, str) for arg in input_args):
        raise TypeError('input_args must be a list of strings')
    if global_args is not None and (
        not isinstance(global_args, list) or not all(isinstance(arg, str) for arg in global_args)
    ):
        raise TypeError('global_args must be a list of strings or None')

    output_kwargs = resolve_ffmpeg_output_kwargs(
        encoding,
        ffmpeg_crf=ffmpeg_crf,
        ffmpeg_preset=ffmpeg_preset,
        ffmpeg_options=ffmpeg_options,
        default_crf=default_crf,
        default_preset=default_preset,
        extra_output_kwargs=extra_output_kwargs,
    )

    command = ['ffmpeg']
    if overwrite_output:
        command.append('-y')
    if global_args is not None:
        command.extend(global_args)
    command.extend(input_args)
    command.extend(_convert_ffmpeg_output_kwargs_to_cli_args(output_kwargs))
    command.append(output_path)
    return command
