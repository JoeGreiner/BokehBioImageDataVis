import logging
from bokeh.models import Div
from pandas.api.types import is_float_dtype

from BokehBioImageDataVis.src.file_handling import sanitize_media_path_value
from BokehBioImageDataVis.src.utils import detect_if_key_is_float

from urllib.parse import quote


BBDV_DOM_HELPER_JS = r"""
function bbdv_normalize_view(value) {
    const view = Array.isArray(value) ? value[value.length - 1] : value;
    return view != null && view.model != null ? view : null;
}

function bbdv_extract_view(value, model, model_id) {
    const view = bbdv_normalize_view(value);
    if (view != null && view.model != null && (view.model === model || view.model.id === model_id)) {
        return view;
    }
    return null;
}

function bbdv_view_children(view) {
    const children = [];
    if (view == null) {
        return children;
    }
    if (typeof view.children === "function") {
        try {
            for (const child of view.children()) {
                if (child != null) {
                    children.push(child);
                }
            }
        } catch (_) {}
    }
    for (const container of [view.child_views, view._child_views, view.renderer_views, view.tool_views]) {
        if (container == null) {
            continue;
        }
        if (Array.isArray(container)) {
            for (const child of container) {
                if (child != null) {
                    children.push(child);
                }
            }
        } else if (typeof container.values === "function") {
            for (const child of container.values()) {
                if (child != null) {
                    children.push(child);
                }
            }
        }
    }
    return children;
}

function bbdv_find_view_in_tree(value, model, model_id, seen) {
    const view = bbdv_normalize_view(value);
    if (view == null || seen.has(view)) {
        return null;
    }
    seen.add(view);
    if (view.model === model || view.model.id === model_id) {
        return view;
    }
    for (const child of bbdv_view_children(view)) {
        const found = bbdv_find_view_in_tree(child, model, model_id, seen);
        if (found != null) {
            return found;
        }
    }
    return null;
}

function bbdv_iter_view_container(container, model, model_id) {
    if (container == null) {
        return null;
    }
    if (typeof container.values === "function") {
        for (const value of container.values()) {
            const view = bbdv_find_view_in_tree(value, model, model_id, new Set());
            if (view != null) {
                return view;
            }
        }
    }
    if (typeof container[Symbol.iterator] === "function") {
        for (const value of container) {
            const view = bbdv_find_view_in_tree(value, model, model_id, new Set());
            if (view != null) {
                return view;
            }
        }
    }
    for (const key in container) {
        const view = bbdv_find_view_in_tree(container[key], model, model_id, new Set());
        if (view != null) {
            return view;
        }
    }
    return null;
}

function bbdv_get_view(model) {
    if (model == null) {
        return null;
    }
    const model_id = model.id;
    const indexes = [];
    if (typeof cb_context !== "undefined" && cb_context != null && cb_context.index != null) {
        indexes.push(cb_context.index);
    }
    if (typeof Bokeh !== "undefined" && Bokeh.index != null) {
        indexes.push(Bokeh.index);
    }
    for (const index of indexes) {
        for (const method of ["get_one", "get", "get_by_id"]) {
            if (typeof index[method] === "function") {
                for (const key of [model, model_id]) {
                    if (key == null) {
                        continue;
                    }
                    try {
                        const view = index[method](key);
                        if (view != null) {
                            return view;
                        }
                    } catch (_) {}
                }
            }
        }
        for (const container of [index, index._views, index.views]) {
            const view = bbdv_iter_view_container(container, model, model_id);
            if (view != null) {
                return view;
            }
        }
    }
    return null;
}

function bbdv_model_el(model) {
    const view = bbdv_get_view(model);
    if (view == null) {
        return null;
    }
    return view.el != null ? view.el : null;
}

function bbdv_query_root(model) {
    const view = bbdv_get_view(model);
    if (view == null) {
        return null;
    }
    if (view.shadow_el != null) {
        return view.shadow_el;
    }
    if (view.el != null) {
        return view.el;
    }
    return null;
}

function bbdv_query_element(model, selector) {
    const root = bbdv_query_root(model);
    if (root != null && typeof root.querySelector === "function") {
        const result = root.querySelector(selector);
        if (result != null) {
            return result;
        }
    }
    if (typeof document !== "undefined") {
        return document.querySelector(selector);
    }
    return null;
}

function bbdv_query_all(models, selector) {
    const model_list = Array.isArray(models) ? models : [models];
    const results = [];
    for (const model of model_list) {
        const root = bbdv_query_root(model);
        if (root != null && typeof root.querySelectorAll === "function") {
            for (const element of root.querySelectorAll(selector)) {
                if (!results.includes(element)) {
                    results.push(element);
                }
            }
        }
    }
    return results;
}

function bbdv_find_element(model, element_id) {
    const selector = `[data-bbdv-id="${element_id}"], [id="${element_id}"]`;
    const element = bbdv_query_element(model, selector);
    if (element != null) {
        return element;
    }
    if (typeof document !== "undefined") {
        return document.getElementById(element_id);
    }
    return null;
}

function bbdv_registered_videos(models) {
    const videos = bbdv_query_all(models, "video");
    if (window._bbdvVideos != null) {
        for (const video of Array.from(window._bbdvVideos)) {
            if (video.isConnected && !videos.includes(video)) {
                videos.push(video);
            }
        }
    }
    return videos;
}
"""


def image_html_and_callback(unique_html_id, df, key, height=None, width=None, image_height=None, image_width=None,
                            title=None, margin_title=5):
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
        image_height_str = f'height:{height}px;'
    else:
        image_height_str = ''
    if width is not None:
        image_width_str = f'width:{width}px;'
    else:
        image_width_str = ''

    if title is not None:
        title_html = f'<div style="text-align: center; margin-bottom: {margin_title}px; font-weight: bold;">\n' \
                     f'    <span>{title}</span>\n' \
                     f'</div>'
    else:
        title_html = ''

    path_to_image = sanitize_media_path_value(df[key].iloc[0])
    # slash replacement is for Windows/Edge compatability
    path_to_image = path_to_image.replace('\\', '/')
    # escape # in the path
    path_to_image = quote(path_to_image)
    path_to_image = path_to_image.replace('#', '%23')
    html_img = (f'<div style="position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center; {image_height_str} {image_width_str}">\n'
                f'{title_html}'
                f'  <img\n'
                f'    src="{path_to_image}"\n'
                f'    id="{unique_html_id}"\n'
                f'    data-bbdv-id="{unique_html_id}"\n'
                '    style="width: 100%; max-height: 100%; margin: 0px 15px 15px 0px; object-fit: contain"\n'
                '   ></img>\n'
                '</div>')

    div_img = Div(width=width, height=height, width_policy="fixed",
                  text=html_img)

    callback_img = (BBDV_DOM_HELPER_JS +
                    "const indices = cb_data.index.indices\n"
                    "if(indices.length > 0){\n"
                    "    const index = indices[0];\n"
                    f'    const path = source.data["{key}"][index].replace(/\\\\/g, "/");\n'
                    "    const encodedPath = encodeURI(path).replace(/#/g, '%23');\n"
                    f'    const imageElement = bbdv_find_element(div, "{unique_html_id}");\n'
                    "    if (imageElement != null) {\n"
                    "        imageElement.src = encodedPath;\n"
                    "    }\n"
                    "}")

    return div_img, callback_img


def get_index_0_text(df, df_keys_to_show):
    row = df.iloc[0]
    lines = []
    for key, value in row.items():
        if key not in df_keys_to_show:
            continue
        if key == 'active_axis_x' or key == 'active_axis_y':
            continue
        # there is an problem sometimes with identifying floats.
        #saving and reloading a dataframe fixes this, but this also should deal with most cases
        if is_float_dtype(value) or isinstance(value, float):

            lines.append(f"<b>{key}</b>: {value:.2f}<br>")
        else:
            lines.append(f"<b>{key}</b>: {value}<br>")
    return ''.join(lines)

def text_html_and_callback(unique_id, df, df_keys_to_show, float_precision, width, height,
                           container_width=None, container_height=None, df_keys_to_ignore=None, div_var='div'):
    # deprecated: container_width, container_height
    if container_width is not None:
        width = container_width
        logging.warning("container_width is deprecated. Use width instead.")
    if container_height is not None:
        height = container_height
        logging.warning("container_height is deprecated. Use height instead.")

    prefix = (BBDV_DOM_HELPER_JS +
              "const indices = cb_data.index.indices;\n"
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
        #         # there is an problem sometimes with identifying floats.
        #         # saving and reloading a dataframe fixes this, but this also should deal with most cases
        if detect_if_key_is_float(df, key):
            line = f'        textElement.innerHTML {assignment_char} ' \
                   f'"<b>{key}</b>:" + " " + source.data["{key}"][index]' \
                   f'.toFixed({float_precision}).toString() + "<br>";\n'
        else:
            line = f'        textElement.innerHTML {assignment_char} ' \
                   f'"<b>{key}</b>:" + " " + source.data["{key}"][index].toString() + "<br>";\n'
        assignment_char = '+='
        combined_str += line

    js_update_str = (f'    const textElement = bbdv_find_element({div_var}, "{unique_id}");\n'
                     '    if (textElement != null) {\n'
                     f'{combined_str}'
                     '    }\n')
    postfix = "}"
    callback_text = f'{prefix}\n{js_update_str}\n{postfix}'

    index_0_text = get_index_0_text(df, df_keys_to_show=df_keys_to_show)

    div_text = Div(width=width, height=height, height_policy="fixed",
                   text=f"<div id='{unique_id}' data-bbdv-id='{unique_id}' style='clear:left; float: left; margin: 0px 15px 15px 0px;';>"
                        f"{index_0_text}"
                        f"</div>")
    return div_text, callback_text, js_update_str


def video_html_and_callback(unique_html_id, df, key, video_height=None, video_width=None, title=None,
                            margin_title=5, autoplay=True, sync_count=1):
    if video_height is not None:
        video_height_str = f'height:{video_height}px;'
    else:
        video_height_str = ''
    if video_width is not None:
        video_width_str = f'width:{video_width}px;'
    else:
        video_width_str = ''

    if title is not None:
        title_html = f'    <div style="text-align: center; margin-bottom: {margin_title}px; font-weight: bold;">\n' \
                     f'        <span>{title}</span>\n' \
                     f'    </div>'
    else:
        title_html = ''

    if autoplay:
        autoplay_attr = 'autoplay '
        sync_class = 'sync-autoplay'
        # Inline event handler for synchronisation.
        # Each video is immediately paused and added to a global ready-set.
        sync_handler_js = (
            "(function(v){"
            "if(!window._bbdvVideos)window._bbdvVideos=new Set();"
            "window._bbdvVideos.add(v);"
            "if(!window._vSync)window._vSync={r:new Set(),ok:false};"
            "if(!window._vSync.ok){"
            "v.pause();"
            "window._vSync.r.add(v.id);"
            "var a=Array.from(window._bbdvVideos).filter(function(x){return x.isConnected&&x.classList.contains('sync-autoplay');});"
            "var n=parseInt(v.getAttribute('data-bbdv-sync-count')||a.length||'1',10);"
            "if(window._vSync.r.size>=n){"
            "window._vSync.ok=true;"
            "a.forEach(function(x){x.currentTime=0;x.play().catch(function(){});});"
            "}"
            "}"
            "})(this)"
        )
        sync_events = f''' oncanplay="{sync_handler_js}" onplay="{sync_handler_js}"'''
    else:
        autoplay_attr = ''
        sync_class = ''
        sync_events = ''

    path_to_video = sanitize_media_path_value(df[key].iloc[0])
    # slash replacement is for Windows/Edge compatability
    path_to_video = path_to_video.replace('\\', '/')
    path_to_video = quote(path_to_video)
    path_to_video = path_to_video.replace('#', '%23')

    html_string = (
        f'<div style="position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center; {video_height_str} {video_width_str}">'
        f'{title_html}'
        f'    <video controls {autoplay_attr}preload="auto" muted loop id="{unique_html_id}" data-bbdv-id="{unique_html_id}" data-bbdv-sync-count="{sync_count}" class="{sync_class}"{sync_events} data-value="firstvalue" style="width: 100%; max-height: 100%; object-fit: contain">'
        f'        <source src="{path_to_video}" type="video/mp4">'
        f'        Your browser does not support the video tag.'
        '    </video>'
        '</div>'
        '')
    div_html = Div(width=video_width, width_policy="fixed", height=video_height, text=html_string)

    # slash replacement is for Windows/Edge compatability
    # After changing the source we only need to reset the sync state.
    # The browser will load the new source and fire canplay automatically,
    # which triggers the oncanplay handler above to re-synchronise.
    callback_video = \
        (BBDV_DOM_HELPER_JS +
         "const indices = cb_data.index.indices;\n"
         "if(indices.length > 0){\n"
         "    const index = indices[0];\n"
         f'    const videoElement = bbdv_find_element(div, "{unique_html_id}");\n'
         '    if (videoElement == null) { return; }\n'
         '    if (!window._bbdvVideos) { window._bbdvVideos = new Set(); }\n'
         '    window._bbdvVideos.add(videoElement);\n'
         '    const old_index = videoElement.getAttribute("data-value");\n'
         '    if(index != old_index){\n'
         f'        videoElement.src = encodeURI(source.data["{key}"][index].replace(/\\\\/g, "/")).replace(/#/g, "%23");\n'
         '        videoElement.setAttribute("data-value", index);\n'
         '        if (window._vSync) { window._vSync = {r: new Set(), ok: false}; }\n'
         '    }\n'
         "}")

    return div_html, callback_video
