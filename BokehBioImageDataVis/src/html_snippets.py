import logging
import uuid

import pandas as pd
from bokeh.models import Div
from pandas.core.dtypes.common import is_float_dtype


def image_html_and_callback(unique_html_id, df, key, height=None, width=None, image_height=None, image_width=None):
    # deprecated: image_height and image_width
    if image_height is not None:
        logging.warning('Warning: image_height is deprecated. Use height instead.')
        height = image_height
    if image_width is not None:
        logging.warning('Warning: image_width is deprecated. Use width instead.')
        width = image_width

    #  only set image height for now to maintain aspect ratio
    # TODO: make this more flexible

    if height is not None:
        image_height_str = f'height="{height}"'
    else:
        image_height_str = ''
    if width is not None:
        image_width_str = f'width="{width}"'
    else:
        image_width_str = ''

    html_img = (f'<img\n'
                f'    src="{df[key][0]}" {image_height_str}\n'
                f'    id="{unique_html_id}"\n'
                '    style="float: left; margin: 0px 15px 15px 0px;"\n'
                '></img>\n'
                '')

    div_img = Div(width=width, height=height, width_policy="fixed",
                  text=html_img)

    callback_img = ("const indices = cb_data.index.indices\n"
                    "if(indices.length > 0){\n"
                    "    const index = indices[0];\n"
                    f'   document.getElementById("{unique_html_id}").src = source.data["{key}"][index];\n'
                    "}")

    return div_img, callback_img


def get_index_0_text(df):
    row = df.iloc[0]
    lines = []
    for key, value in row.items():
        if key == 'active_axis_x' or key == 'active_axis_y':
            continue
        if pd.api.types.is_float_dtype(value):
            lines.append(f"<b>{key}</b>: {value:.2f}<br>")
        else:
            lines.append(f"<b>{key}</b>: {value}<br>")
    return ''.join(lines)

def text_html_and_callback(unique_id, df, df_keys_to_show, float_precision, width, height,
                           container_width=None, container_height=None, df_keys_to_ignore=None):
    # deprecated: container_width, container_height
    if container_width is not None:
        width = container_width
        logging.warning("container_width is deprecated. Use width instead.")
    if container_height is not None:
        height = container_height
        logging.warning("container_height is deprecated. Use height instead.")

    prefix = ("const indices = cb_data.index.indices;\n"
              "if(indices.length > 0){\n"
              "    const index = indices[0];")

    combined_str = ""
    assignment_char = '='
    if df_keys_to_show is None:
        df_keys_to_show = list(df.keys())
    if df_keys_to_ignore is not None:
        for key in df_keys_to_ignore:
            if key in df_keys_to_show:
                df_keys_to_show.remove(key)
    for key in df_keys_to_show:
        if key == 'active_axis_x' or key == 'active_axis_y':
            continue
        if is_float_dtype(df[key]):
            line = f'    document.getElementById("{unique_id}").innerHTML {assignment_char} ' \
                   f'"<b>{key}</b>:" + " " + source.data["{key}"][index]' \
                   f'.toFixed({float_precision}).toString() + "<br>";\n'
        else:
            line = f'    document.getElementById("{unique_id}").innerHTML {assignment_char} ' \
                   f'"<b>{key}</b>:" + " " + source.data["{key}"][index].toString() + "<br>";\n'
        assignment_char = '+='
        combined_str += line

    postfix = "}"
    callback_text = f'{prefix}\n{combined_str}\n{postfix}'

    index_0_text = get_index_0_text(df)

    div_text = Div(width=width, height=height, height_policy="fixed",
                   text=f"<div id='{unique_id}' style='clear:left; float: left; margin: 0px 15px 15px 0px;';>"
                        f"{index_0_text}"
                        f"</div>")
    return div_text, callback_text, combined_str


def video_html_and_callback(unique_html_id, df, key, video_height=None, video_width=None):
    if video_height is not None:
        video_height_str = f'height="{video_height}"'
    else:
        video_height_str = ''
    if video_width is not None:
        video_width_str = f'width="{video_width}"'
    else:
        video_width_str = ''

    html_string = (
        f'<div style="position: relative; display: flex; justify-content: center; align-items: center; height: {video_height_str}; width: {video_width_str};">'
        f'    <video controls autoplay muted loop id="{unique_html_id}" data-value="firstvalue" style="max-height: 100%; max-width: 100%;">'
        f'        <source src="{df[key][0]}" type="video/mp4">'
        f'        Your browser does not support the video tag.'
        '    </video>'
        '</div>'
        '')
    div_html = Div(width=video_width, width_policy="fixed", height=video_height, text=html_string)

    callback_video = \
        ("const indices = cb_data.index.indices;\n"
         "if(indices.length > 0){\n"
         "    const index = indices[0];\n"
         f'    const old_index = document.getElementById("{unique_html_id}").getAttribute("data-value");\n'
         '    if(index != old_index){\n'
         f'        document.getElementById("{unique_html_id}").src = source.data["{key}"][index];\n'
         f'        document.getElementById("{unique_html_id}").setAttribute("data-value", index);\n'
         '    }\n'
         "}")

    return div_html, callback_video
