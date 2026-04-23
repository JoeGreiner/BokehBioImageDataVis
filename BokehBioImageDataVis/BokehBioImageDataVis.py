import hashlib
import json
import os.path
import shutil
import uuid
import warnings
from collections import Counter, defaultdict
from fractions import Fraction
from os.path import join
import ffmpeg
import pandas as pd
from bokeh.io import show, output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, CDSView, Select, CustomJS, HoverTool, LayoutDOM, Slider, Button, Div, LegendItem
from bokeh.palettes import Category10, Category20
from bokeh.plotting import figure
import logging

from BokehBioImageDataVis.src.bokeh_helpers.get_bokeh_images_base64 import get_pan_tool_image, get_rect_zoom_image, \
    get_mouse_wheel_image, get_reset_image, get_hover_tool_image
from BokehBioImageDataVis.src.colormapping import random_color
from BokehBioImageDataVis.src.ffmpeg_config import build_ffmpeg_output_stream, resolve_ffmpeg_output_kwargs
from BokehBioImageDataVis.src.file_handling import copy_files_to_output_dir, create_file, sanitize_media_path_column, \
    sanitize_media_path_value
from BokehBioImageDataVis.src.html_snippets import image_html_and_callback, text_html_and_callback, \
    video_html_and_callback
from BokehBioImageDataVis.src.utils import identify_numerical_variables


class BokehBioImageDataVis:
    def __init__(self, df,
                 scatter_width=600, scatter_height=600, scatter_size=10,
                 scatterplot_select_options_width=100,
                 do_scatter_data_hover=True,
                 scatter_data_hover_float_precision=2,
                 x_axis_key=None,
                 y_axis_key=None,
                 category_key=None,
                 dropdown_options=None,
                 add_id_to_dataframe=True,
                 do_copy_files_to_output_dir=True,
                 copy_files_dir_level=1,
                 clearOutputFolderIfNotEmpty=False,
                 legend_position = "bottom_right",
                 legend_title=None,
                 output_filename='BokehBioImageDataVis.html',
                 output_title=None, ):
        '''
        Initialize the main object, where the data is stored and the scatter plot is created.
        Can be used to create a scatter plot with images and videos as hover.

        :param df: pd.DataFrame with data to visualize
        :param scatter_width: width of scatter plot
        :param scatter_height: height of scatter plot
        :param scatter_size: size of scatter points
        :param do_scatter_data_hover: add a hover circle around active scatter point
        :param scatter_data_hover_float_precision: precision of hover text data, when floats are converted to strings
        :param x_axis_key: default x axis key
        :param y_axis_key: default y axis key
        :param category_key: if a category key is given, the scatter points are colored according to this key
        :param dropdown_options: can be used to filter the dropdown options to only relevant ones, list of strings
        :param add_id_to_dataframe: add an id column to the dataframe, which can be used with the slider
        :param do_copy_files_to_output_dir: copy files to output dir, relative paths, to make everything portable
        :param copy_files_dir_level: how many levels of the folder structure should be preserved when copying files
        :param clearOutputFolderIfNotEmpty: if output folder is not empty, delete contents
        :param legend_position: position of the legend, can be 'bottom_right', 'bottom_left', 'top_left', 'top_right', 'outside'
        :param legend_title: title of the legend
        :param output_filename: html output filename
        :param output_title: title of the html output
        '''
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')



        self.df = df.copy()
        self.add_id_to_dataframe = add_id_to_dataframe

        if category_key:
            logging.info(f'Category key: {category_key}')
            self.category_key = category_key
        else:
            self.category_key = None
        self.legend_position =  legend_position
        self.legend_title = legend_title
        allowed_positions = ['bottom_right', 'bottom_left', 'top_left', 'top_right', 'outside']
        assert self.legend_position in allowed_positions, (f'legend position must be in {allowed_positions}, got'
                                                           f'{self.legend_position}')

        self.output_folder = os.path.dirname(output_filename)
        if self.output_folder == '':
            self.output_folder = '.'  # current folder
        logging.info(f'Output folder: {self.output_folder}')

        self.clearOutputFolderIfNotEmpty = clearOutputFolderIfNotEmpty
        if self.output_folder != '.':
            if os.path.exists(self.output_folder):
                if len(os.listdir(self.output_folder)) > 0:
                    logging.warning(f'Output folder is not empty: {self.output_folder}')
                    if self.clearOutputFolderIfNotEmpty:
                        logging.info('Deleting contents of output folder')
                        for filename in os.listdir(self.output_folder):
                            file_path = os.path.join(self.output_folder, filename)
                            try:
                                if os.path.isfile(file_path) or os.path.islink(file_path):
                                    os.unlink(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                            except Exception as e:
                                logging.error('Failed to delete %s. Reason: %s' % (file_path, e))
                        else:
                            logging.info('Keeping contents of output folder')
                else:
                    logging.info('Output folder is empty')
            else:
                logging.info('Output folder does not exist yet')

        logging.info(f'Output filename: {output_filename}')
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # holds tuples of [dataframe_key and html unique ideas]
        self.scatter_figure = None
        self.registered_video_elements = []
        self.registered_image_elements = []

        # touple of id and update function
        self.registered_text_elements = []
        self.dataset_selector = None
        self.dataset_sources = []
        self.dataset_labels = []
        self.dataset_legend_items = []

        self.scatter_marker_key = 'circle'
        self.scatter_color_legend_key = None
        self.scatter_marker_legend_key = None
        self.row_refresh_js = None
        self.main_scatter_renderer = None
        self.scatter_legend = None

        # copy needed files relative to the output dir, e.g. for videos
        # makes the visualisation portable, but also increases the size of the output dir
        # additionally, some of the folder structure may be renamed to resolve uniqueness issues
        logging.info(f'Copy files to output dir: {do_copy_files_to_output_dir}')
        self.do_copy_files_to_output_dir = do_copy_files_to_output_dir

        # to keep some organisation, do not only copy the files, but preserve the folder structure up to the
        # specified level
        logging.info(f'Copy files dir level: {copy_files_dir_level}')
        self.copy_files_dir_level = copy_files_dir_level
        self.used_paths = []  # paths that are already used for data saving/copying (so that there are no duplicates appearing)
        self.copied_paths_by_source = {}  # reuse already copied media when the same source path appears again
        self.generated_media_keys = set()
        self.stacked_video_specs = {}
        self.stacked_video_output_cache = {}

        self.non_data_keys = []
        self.path_keys = []
        numeric_options_df = self.df.copy()
        if self.add_id_to_dataframe and 'id' not in numeric_options_df.columns:
            numeric_options_df.insert(0, 'id', range(0, len(numeric_options_df)))
        self.numeric_options = identify_numerical_variables(numeric_options_df)

        if x_axis_key is None:
            self.x_axis_key = self.numeric_options[1]  # options[0] is the id, 1 is the first real numeric option
        else:
            self.x_axis_key = x_axis_key

        if y_axis_key is None:
            self.y_axis_key = self.numeric_options[2]
        else:
            self.y_axis_key = y_axis_key

        if dropdown_options is None:
            self.dropdown_options = self.numeric_options
        else:
            self.dropdown_options = []
            for option in dropdown_options:
                if option in df.columns:
                    self.dropdown_options.append(option)
                else:
                    logging.warning(f'Warning: couldnt find dropdown option {option} in df, skipping option.')

        self.scatter_width = scatter_width
        self.scatter_height = scatter_height
        self.scatter_size = scatter_size
        self.scatterplot_select_options_width = scatterplot_select_options_width
        self.do_scatter_data_hover = do_scatter_data_hover
        self.scatter_data_hover_float_precision = scatter_data_hover_float_precision

        if output_title is None:
            output_title = os.path.splitext(os.path.basename(output_filename))[0]

        output_file(output_filename, title=output_title, mode="inline")

        self.initialize_data()
        self.initialize_highlighter()

    def show_bokeh(self, obj: LayoutDOM):
        # self.scatter_figure.toolbar_location = None
        self.add_hover_highlight()
        show(obj)

        # create a file that reminds the user to unzip the data folder, this was a common issue
        create_file(filename=join(self.output_folder, 'PLEASE_MAKE_SURE_IM_UNZIPPED.txt'),
                    content="Please make sure to unzip the data folder before opening the html file.")

    def initialize_data(self):
        if self.add_id_to_dataframe and 'id' not in self.df.columns:
            self.df.insert(0, 'id', range(0, len(self.df)))

        self.df['active_axis_x'] = self.df[self.x_axis_key]
        self.df['active_axis_y'] = self.df[self.y_axis_key]

        if self.scatter_color_legend_key and self.scatter_marker_legend_key:
            self.df['legend'] = self.df.apply(
                lambda x: f'{x[self.scatter_color_legend_key]} {x[self.scatter_marker_legend_key]}', axis=1
            )
        elif self.scatter_color_legend_key:
            self.df['legend'] = self.df[self.scatter_color_legend_key]
        elif self.scatter_marker_legend_key:
            self.df['legend'] = self.df[self.scatter_marker_legend_key]
        elif self.category_key:
            self.df['legend'] = self.df[self.category_key]

        if self.category_key:
            # add a color column to the dataframe, one unique color per category
            unique_categories = self.df[self.category_key].unique()

            # if smaller than 11, use tab10, otherwise tab20, if bigger, use random colors
            if len(unique_categories) < 3:
                palette = Category10[3]
            elif len(unique_categories) < 11:
                palette = Category10[len(unique_categories)]
            elif len(unique_categories) < 21:
                palette = Category20[len(unique_categories)]
            else:
                palette = [random_color() for _ in range(len(unique_categories))]
                # convert rgb to hex, e.g. #5254a3
                palette = ['#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255)) for r, g, b in palette]

            # assign to dataframe based on category
            self.df['color_mapping'] = [palette[unique_categories.tolist().index(category)] for category in
                                        self.df[self.category_key]]

        self.csd_source = ColumnDataSource(data=self.df)
        self.csd_view = CDSView(source=self.csd_source)

    def initialize_highlighter(self, init_index=0):
        self.highlight_df = pd.DataFrame({'highlight_x': [self.df['active_axis_x'].iloc[init_index]],
                                          'highlight_y': [self.df['active_axis_y'].iloc[init_index]],
                                          'last_selected_index': [0]})

        self.highlight_csd_source = ColumnDataSource(data=self.highlight_df)
        self.highlight_csd_view = CDSView(source=self.highlight_csd_source)

    def _require_scatter_figure(self):
        if self.scatter_figure is None:
            raise RuntimeError(
                "No scatter figure has been created yet. "
                "Please call 'create_scatter_figure()' before adding hovers, text, sliders, or legends."
            )

    def _remember_media_key(self, key):
        if key not in self.non_data_keys:
            self.non_data_keys.append(key)
        if key not in self.path_keys:
            self.path_keys.append(key)

    def _resolve_media_path(self, path_value):
        path_value = sanitize_media_path_value(path_value)
        if not path_value:
            return ''
        if os.path.isabs(path_value):
            return path_value
        return join(self.output_folder, path_value)

    def _ensure_missing_image_placeholder(self):
        missing_data_icon = 'data_missing.png'
        output_path_missing = join(self.output_folder, 'data', missing_data_icon)
        if not os.path.exists(os.path.dirname(output_path_missing)):
            os.makedirs(os.path.dirname(output_path_missing))
        if not os.path.exists(output_path_missing):
            shutil.copyfile(join(os.path.dirname(__file__), 'resources', 'MissingDataIcon.png'), output_path_missing)
        return join('data', missing_data_icon), output_path_missing

    def _ensure_missing_video_placeholder(self):
        missing_data_mp4 = 'data_missing.mp4'
        output_path_missing = join(self.output_folder, 'data', missing_data_mp4)
        if not os.path.exists(os.path.dirname(output_path_missing)):
            os.makedirs(os.path.dirname(output_path_missing))
        if not os.path.exists(output_path_missing):
            shutil.copyfile(join(os.path.dirname(__file__), 'resources', 'MissingDataVideo.mp4'), output_path_missing)
        return join('data', missing_data_mp4), output_path_missing

    def _prepare_image_column(self, key):
        if key not in self.df.columns:
            raise KeyError(f"Could not find image key '{key}' in the dataframe.")

        self.df = sanitize_media_path_column(self.df, key)
        self.csd_source.data[key] = self.df[key]

        if self.do_copy_files_to_output_dir and key not in self.generated_media_keys:
            self.df, self.used_paths = copy_files_to_output_dir(df=self.df, path_key=key,
                                                                output_folder=self.output_folder,
                                                                used_paths=self.used_paths,
                                                                copy_files_dir_level=self.copy_files_dir_level,
                                                                copied_paths_by_source=self.copied_paths_by_source)
            self.csd_source.data[key] = self.df[key]

        missing_path_relative, _ = self._ensure_missing_image_placeholder()
        for path_img in self.df[key]:
            if not path_img or not os.path.exists(self._resolve_media_path(path_img)):
                logging.warning(f'Path {path_img} does not exist. Replacing with data missing image.')
                self.df[key] = self.df[key].replace(path_img, missing_path_relative)

        self.csd_source.data[key] = self.df[key]

    def _prepare_video_column(self, key):
        if key not in self.df.columns:
            raise KeyError(f"Could not find video key '{key}' in the dataframe.")

        self.df = sanitize_media_path_column(self.df, key)
        self.csd_source.data[key] = self.df[key]

        if self.do_copy_files_to_output_dir and key not in self.generated_media_keys:
            self.df, self.used_paths = copy_files_to_output_dir(df=self.df, path_key=key,
                                                                output_folder=self.output_folder,
                                                                used_paths=self.used_paths,
                                                                copy_files_dir_level=self.copy_files_dir_level,
                                                                copied_paths_by_source=self.copied_paths_by_source)
            self.csd_source.data[key] = self.df[key]

        missing_path_relative, _ = self._ensure_missing_video_placeholder()
        for path_video in self.df[key]:
            if not path_video or not os.path.exists(self._resolve_media_path(path_video)):
                logging.warning(f'Path {path_video} does not exist. Replacing with data missing video.')
                self.df[key] = self.df[key].replace(path_video, missing_path_relative)

        self.csd_source.data[key] = self.df[key]

    def _ensure_ffmpeg_tools_available(self):
        for tool_name in ('ffmpeg', 'ffprobe'):
            if shutil.which(tool_name) is None:
                raise RuntimeError(
                    f"Could not find '{tool_name}' on PATH. "
                    "Please install ffmpeg/ffprobe to use stacked video hovers."
                )

    def _format_ffmpeg_error(self, exc):
        stderr = getattr(exc, 'stderr', b'')
        stdout = getattr(exc, 'stdout', b'')
        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', errors='replace')
        if isinstance(stdout, bytes):
            stdout = stdout.decode('utf-8', errors='replace')
        stderr = (stderr or '').strip()
        stdout = (stdout or '').strip()
        return stderr or stdout or 'No additional error output available.'

    def _run_ffmpeg_stream(self, stream, description):
        try:
            (
                stream
                .global_args('-loglevel', 'error')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as exc:
            raise RuntimeError(f'{description} failed.\n{self._format_ffmpeg_error(exc)}') from exc

    def _probe_video_info(self, video_path):
        self._ensure_ffmpeg_tools_available()
        try:
            probe_data = ffmpeg.probe(
                video_path,
                cmd='ffprobe',
                select_streams='v:0',
                count_frames=None,
                show_entries='stream=width,height,avg_frame_rate,nb_read_frames',
            )
        except ffmpeg.Error as exc:
            raise RuntimeError(f'ffprobe for {video_path} failed.\n{self._format_ffmpeg_error(exc)}') from exc

        stream_info = (probe_data.get('streams') or [None])[0]
        if stream_info is None:
            raise RuntimeError(f'Could not find a video stream in {video_path}.')

        frame_rate_text = str(stream_info.get('avg_frame_rate', ''))
        if frame_rate_text in ('', '0/0'):
            raise RuntimeError(f'Could not determine the average frame rate for {video_path}.')

        frame_count_text = str(stream_info.get('nb_read_frames', ''))
        if frame_count_text in ('', 'N/A'):
            raise RuntimeError(
                f'Could not determine the exact number of frames for {video_path}. '
                'Stacked video hovers require an exact frame count.'
            )

        try:
            frame_count = int(frame_count_text)
        except ValueError as exc:
            raise RuntimeError(f'Could not parse the frame count for {video_path}: {frame_count_text}') from exc

        try:
            fps = Fraction(frame_rate_text)
        except (ValueError, ZeroDivisionError) as exc:
            raise RuntimeError(f'Could not parse the frame rate for {video_path}: {frame_rate_text}') from exc

        if frame_count <= 0:
            raise RuntimeError(f'Video {video_path} does not contain any frames.')
        if fps <= 0:
            raise RuntimeError(f'Video {video_path} has an invalid frame rate: {frame_rate_text}.')

        width = stream_info.get('width')
        height = stream_info.get('height')
        if width is None or height is None:
            raise RuntimeError(f'Could not determine the frame size for {video_path}.')

        return {
            'width': int(width),
            'height': int(height),
            'frame_count': frame_count,
            'fps': fps,
            'fps_text': frame_rate_text,
        }

    def _build_stacked_video_output(self, input_paths, spec):
        _, missing_video_abs = self._ensure_missing_video_placeholder()
        missing_video_abs = os.path.abspath(missing_video_abs)

        resolved_input_paths = []
        for input_path in input_paths:
            resolved_input_path = self._resolve_media_path(input_path)
            if not resolved_input_path or not os.path.exists(resolved_input_path):
                resolved_input_path = missing_video_abs
            resolved_input_paths.append(os.path.abspath(resolved_input_path))

        video_infos = [self._probe_video_info(path) for path in resolved_input_paths]
        real_video_infos = [
            (path, info) for path, info in zip(resolved_input_paths, video_infos)
            if path != missing_video_abs
        ]

        reference_info = real_video_infos[0][1] if real_video_infos else None
        if reference_info is not None:
            for _, info in real_video_infos[1:]:
                if info['frame_count'] != reference_info['frame_count']:
                    raise RuntimeError(
                        'Stacked video inputs must have the same exact number of frames. '
                        f'Found {reference_info["frame_count"]} and {info["frame_count"]} frames.'
                    )
                if info['fps'] != reference_info['fps']:
                    raise RuntimeError(
                        'Stacked video inputs must have the same exact average frame rate. '
                        f'Found {reference_info["fps_text"]} and {info["fps_text"]}.'
                    )

        cell_width = max(info['width'] for info in video_infos)
        cell_height = max(info['height'] for info in video_infos)

        output_kwargs = resolve_ffmpeg_output_kwargs(
            spec['encoding'],
            ffmpeg_crf=spec['ffmpeg_crf'],
            ffmpeg_preset=spec['ffmpeg_preset'],
            ffmpeg_options=spec['ffmpeg_options'],
            extra_output_kwargs={'an': None},
        )

        cache_payload = {
            'stack': spec['stack'],
            'encoding': spec['encoding'],
            'frame_count': None if reference_info is None else reference_info['frame_count'],
            'fps_text': None if reference_info is None else reference_info['fps_text'],
            'cell_width': cell_width,
            'cell_height': cell_height,
            'output_kwargs': output_kwargs,
            'inputs': [
                {
                    'path': path,
                    'size': os.path.getsize(path),
                    'mtime': os.path.getmtime(path),
                }
                for path in resolved_input_paths
            ],
        }

        merged_video_dir = join(self.output_folder, 'data', 'merged_videos')
        if not os.path.exists(merged_video_dir):
            os.makedirs(merged_video_dir)

        cache_hash = hashlib.sha256(
            json.dumps(cache_payload, sort_keys=True, default=str).encode('utf-8')
        ).hexdigest()[:24]
        output_filename = f'stacked_{cache_hash}.mp4'
        output_path_absolute = join(merged_video_dir, output_filename)
        output_path_relative = join('data', 'merged_videos', output_filename)

        if os.path.exists(output_path_absolute):
            return output_path_relative

        needs_placeholder_normalization = reference_info is not None
        input_signatures = [
            (input_path, needs_placeholder_normalization and input_path == missing_video_abs)
            for input_path in resolved_input_paths
        ]
        signature_counts = Counter(input_signatures)
        signature_usage = defaultdict(int)
        base_streams_by_signature = {}
        for signature, count in signature_counts.items():
            path, loop_input = signature
            input_kwargs = {}
            if loop_input:
                input_kwargs['stream_loop'] = -1
            base_stream = ffmpeg.input(path, **input_kwargs).video
            if count == 1:
                base_streams_by_signature[signature] = [base_stream]
            else:
                split_stream = base_stream.filter_multi_output('split')
                base_streams_by_signature[signature] = [split_stream[index] for index in range(count)]

        prepared_streams = []
        for signature in input_signatures:
            branch_index = signature_usage[signature]
            signature_usage[signature] += 1
            stream = base_streams_by_signature[signature][branch_index]
            if reference_info is not None:
                stream = stream.filter('fps', reference_info['fps_text'])
                stream = stream.filter('trim', end_frame=reference_info['frame_count'])
            stream = stream.filter('setpts', 'PTS-STARTPTS')
            stream = stream.filter(
                'scale',
                cell_width,
                cell_height,
                force_original_aspect_ratio='decrease',
            )
            stream = stream.filter(
                'pad',
                cell_width,
                cell_height,
                '(ow-iw)/2',
                '(oh-ih)/2',
                color='white',
            )
            stream = stream.filter('setsar', '1')
            prepared_streams.append(stream)

        stack_operator = 'vstack' if spec['stack'] == 'column' else 'hstack'
        stacked_stream = ffmpeg.filter(prepared_streams, stack_operator, inputs=len(prepared_streams))
        stacked_stream = stacked_stream.filter('pad', 'ceil(iw/2)*2', 'ceil(ih/2)*2', color='white')

        ffmpeg_stream = build_ffmpeg_output_stream(
            stacked_stream,
            output_path=output_path_absolute,
            encoding=spec['encoding'],
            ffmpeg_crf=spec['ffmpeg_crf'],
            ffmpeg_preset=spec['ffmpeg_preset'],
            ffmpeg_options=spec['ffmpeg_options'],
            extra_output_kwargs={'an': None},
        )
        self._run_ffmpeg_stream(ffmpeg_stream, f'ffmpeg stacked video export for {output_filename}')
        return output_path_relative

    def _prepare_media_key_for_dataset(self, key, prepared_media_keys=None, prefer_video=False):
        if prepared_media_keys is not None and key in prepared_media_keys:
            return

        if key in self.stacked_video_specs:
            self._materialize_stacked_video_column(key, prepared_media_keys=prepared_media_keys)
        elif prefer_video:
            self._prepare_video_column(key)
        elif any(element['key'] == key for element in self.registered_image_elements):
            self._prepare_image_column(key)
        else:
            self._prepare_video_column(key)

        if prepared_media_keys is not None:
            prepared_media_keys.add(key)

    def _materialize_stacked_video_column(self, key, prepared_media_keys=None):
        spec = self.stacked_video_specs[key]
        for source_key in spec['keys']:
            self._prepare_media_key_for_dataset(
                source_key,
                prepared_media_keys=prepared_media_keys,
                prefer_video=True,
            )

        stacked_video_paths = []
        stacked_video_cache = self.stacked_video_output_cache.setdefault(key, {})
        for row_index in range(len(self.df)):
            row_input_paths = tuple(
                sanitize_media_path_value(self.df[source_key].iloc[row_index])
                for source_key in spec['keys']
            )
            if row_input_paths not in stacked_video_cache:
                stacked_video_cache[row_input_paths] = self._build_stacked_video_output(row_input_paths, spec)
            stacked_video_paths.append(stacked_video_cache[row_input_paths])

        self.df[key] = stacked_video_paths
        self.csd_source.data[key] = self.df[key]

        if prepared_media_keys is not None:
            prepared_media_keys.add(key)

    def create_scatter_figure(self, colorKey=None, markerKey=None, colorLegendKey=None, markerLegendKey=None, scatter_alpha=0.5, highlight_alpha=0.3):
        self.scatter_marker_key = markerKey or 'circle'
        self.scatter_color_legend_key = colorLegendKey
        self.scatter_marker_legend_key = markerLegendKey
        self.initialize_data()

        self.scatter_figure = figure(height=self.scatter_height,
                                    width=self.scatter_width,
                                     x_axis_label=self.x_axis_key,
                                     y_axis_label=self.y_axis_key,
                                     tools="pan,wheel_zoom,box_zoom,reset")

        self.scatter_figure.scatter('highlight_x', 'highlight_y',
                                   source=self.highlight_csd_source, view=self.highlight_csd_view,
                                   size=3 * self.scatter_size, color="red", alpha=highlight_alpha
                                   )

        if colorKey:
            logging.info(f'Using {colorKey} as color key and {colorLegendKey} for legend.')
            self.main_scatter_renderer = self.scatter_figure.scatter('active_axis_x', 'active_axis_y',
                                                                     source=self.csd_source, view=self.csd_view,
                                                                     size=self.scatter_size,
                                                                     alpha=scatter_alpha,
                                                                     marker=self.scatter_marker_key,
                                                                     color=colorKey, legend_group="legend",
                                                                     name='main_graph')
        elif self.category_key:
            logging.info(f'Using {self.category_key} as color key.')
            self.main_scatter_renderer = self.scatter_figure.scatter('active_axis_x', 'active_axis_y',
                                                                     source=self.csd_source, view=self.csd_view,
                                                                     size=self.scatter_size,
                                                                     alpha=scatter_alpha,
                                                                     marker=self.scatter_marker_key,
                                                                     color='color_mapping', legend_group="legend",
                                                                     name='main_graph')
        else:
            scatter_kwargs = dict(
                source=self.csd_source,
                view=self.csd_view,
                size=self.scatter_size,
                name='main_graph',
                alpha=scatter_alpha,
                marker=self.scatter_marker_key,
            )
            if self.scatter_marker_legend_key:
                scatter_kwargs['legend_group'] = "legend"
            self.main_scatter_renderer = self.scatter_figure.scatter('active_axis_x', 'active_axis_y', **scatter_kwargs)

        if self.scatter_figure.legend:
            if self.legend_position.lower() == "outside":
                legend_obj = self.scatter_figure.legend[0]
                self.scatter_figure.legend.remove(legend_obj)
                self.scatter_figure.add_layout(legend_obj, 'right')
                self.scatter_legend = legend_obj
            else:
                self.scatter_figure.legend.location = self.legend_position
                self.scatter_legend = self.scatter_figure.legend[0]

            # change legend background alpha
            self.scatter_figure.legend.background_fill_alpha = 0.5
            # show the title of the legend
            self.scatter_figure.legend.title = self.category_key
            if self.legend_title:
                self.scatter_figure.legend.title = self.legend_title
        else:
            self.scatter_legend = None

        self.axesselect_x = Select(title="X-Axis:", value=self.x_axis_key, options=self.dropdown_options)
        self.axesselect_x.js_on_change('value',
                                       CustomJS(args=dict(source=self.csd_source,
                                                          highlight_df=self.highlight_csd_source,
                                                          axesselect_x=self.axesselect_x,
                                                          xaxis=self.scatter_figure.xaxis[0]),
                                                code="""
          source.data['active_axis_x'] = source.data[axesselect_x.value];
          source.change.emit();
          const last_index = highlight_df.data["last_selected_index"][0];
          highlight_df.data["highlight_x"][0] =  source.data[axesselect_x.value][last_index];
          console.log(last_index);
          highlight_df.change.emit();
          xaxis.axis_label = axesselect_x.value;
          """))

        self.axesselect_y = Select(title="Y-Axis:", value=self.y_axis_key, options=self.dropdown_options)
        self.axesselect_y.js_on_change('value',
                                       CustomJS(args=dict(source=self.csd_source,
                                                          highlight_df=self.highlight_csd_source,
                                                          axesselect_y=self.axesselect_y,
                                                          yaxis=self.scatter_figure.yaxis[0]),
                                                code="""
          source.data['active_axis_y'] = source.data[axesselect_y.value];
          source.change.emit();
          const last_index = highlight_df.data["last_selected_index"][0];
          highlight_df.data["highlight_y"][0] =  source.data[axesselect_y.value][last_index];
          highlight_df.change.emit();
          yaxis.axis_label = axesselect_y.value;
          """))

        controls = [self.axesselect_x, self.axesselect_y]
        self.scatterplot_select_options = column(*controls, width=self.scatterplot_select_options_width)
        self.scatterplot_select_options.css_classes = ["dropdown_controls"]

        return row([self.scatterplot_select_options, Div(text="", width=4), self.scatter_figure])

    def add_hover_highlight(self):
        self._require_scatter_figure()

        # TODO: probably can remove last_selected index in uuids and in all the other hovers and just use this one here?
        code_hover_highlight = ("const indices = cb_data.index.indices;\n"
                                "if(indices.length > 0){\n"
                                "    const index = indices[0];\n"
                                '    highlight_df.data["highlight_x"][0] = source.data["active_axis_x"][index];\n'
                                '    highlight_df.data["highlight_y"][0] = source.data["active_axis_y"][index];\n'
                                "    highlight_df.data['last_selected_index'][0] = index;\n"
                                '    highlight_df.change.emit();\n')

        # check if self.manual_id_selection_slider exists
        if hasattr(self, 'manual_id_selection_slider'):
            code_hover_highlight += "    manual_id_selection.value = index;\n"

        code_hover_highlight += "}"

        if hasattr(self, 'manual_id_selection_slider'):
            img_js_callback = CustomJS(
                args=dict(source=self.csd_source, manual_id_selection=self.manual_id_selection_slider,
                          highlight_df=self.highlight_csd_source),
                code=code_hover_highlight)
        else:
            img_js_callback = CustomJS(
                args=dict(source=self.csd_source, highlight_df=self.highlight_csd_source),
                code=code_hover_highlight)

        img_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        img_hover_tool.callback = img_js_callback

        self.scatter_figure.add_tools(img_hover_tool)

    def add_image_hover(self, key, height=300, width=300, image_width=None, image_height=None, legend_text="",
                        title=None):
        if self.dataset_selector is not None:
            raise RuntimeError("Please add the dataset selector after adding image hovers.")
        self._require_scatter_figure()
        # deprecated: image_width and image_height are not used anymore
        if image_width is not None:
            width = image_width
            logging.warning("image_width is deprecated and not used anymore. Use width instead")
        if image_height is not None:
            height = image_height
            logging.warning("image_height is deprecated and not used anymore. Use height instead")

        self._remember_media_key(key)
        self._prepare_image_column(key)

        unique_html_id = uuid.uuid4()
        image_update_js = (f'    const path = source.data["{key}"][index].replace(/\\\\/g, "/");\n'
                           "    const encodedPath = encodeURI(path).replace(/#/g, '%23');\n"
                           f'    document.getElementById("{unique_html_id}").src = encodedPath;\n')
        div_img, callback_img = image_html_and_callback(unique_html_id=unique_html_id,
                                                        df=self.df, key=key,
                                                        height=height, width=width,
                                                        title=title)
        self.registered_image_elements.append({
            'id': unique_html_id,
            'key': key,
            'legend_text': legend_text,
            'div': div_img,
            'height': height,
            'width': width,
            'title': title,
            'js_update': image_update_js,
        })

        img_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_img),
                                   code=callback_img)

        img_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        img_hover_tool.callback = img_JS_callback

        self.scatter_figure.add_tools(img_hover_tool)

        return div_img

    def add_toggle_video_button(self):
        width_button = (self.scatter_width + self.scatterplot_select_options_width) // 2
        self.toggleVideoButton = Button(label="Toggle Pause/Play Videos", button_type="success",
                                         css_classes=["video-toggle-button"], width = width_button)
        button_code_video = """
        var videos = document.getElementsByTagName('video');
        console.log(videos);
        for (var i = 0; i < videos.length; i++) {
            if (videos[i].paused) {
                videos[i].play();
            } else {
              videos[i].pause();
            }
        }
        """

        self.toggleVideoButton.js_on_click(CustomJS(code=button_code_video))
        return self.toggleVideoButton


    def add_legend(self, background_alpha=0.75):
        toggle_js = """
        var button = document.querySelector('.highlight-button button');
        if (button.innerText == "Show Legend") {
            button.innerText = "Hide Legend";
            button.classList.remove("bk-btn-success");
            button.classList.add("bk-btn-warning");
        } else {
            button.innerText = "Show Legend";
            button.classList.remove("bk-btn-warning");
            button.classList.add("bk-btn-success");
        }
        """

        width_button = (self.scatter_width + self.scatterplot_select_options_width) // 2
        self.toggleLegendButton = Button(label="Show Legend", button_type="success",
                                         css_classes=["highlight-button"], width = width_button)
        self.toggleLegendButton.js_on_click(CustomJS(code=toggle_js))


        ids_of_img = [str(thing['id']) for thing in self.registered_image_elements]
        text_of_img = [thing['legend_text'] for thing in self.registered_image_elements]
        ids_of_vids = [str(thing['id']) for thing in self.registered_video_elements]
        text_of_vids = [thing['legend_text'] for thing in self.registered_video_elements]
        ids = ids_of_img + ids_of_vids
        text = text_of_img + text_of_vids

        # replace accidentals \n with br
        text = [t.replace('\n', '<br>') for t in text]


        legend_scatter = (f'<p>Hover with the mouse over individual scatter points to explore the data.</p>'
                          f'<p><img src={get_pan_tool_image()}></img> Toggle pan tool.<br> Use left mouse click and drag to pan.</p>'
                          f'<p><img src={get_rect_zoom_image()}></img> Toggle box zoom tool.<br> Use left mouse click and drag to zoom.</p>'
                          f'<p><img src={get_mouse_wheel_image()}></img> Toggle wheel zoom tool.<br> Use mouse wheel to zoom.</p>'
                          f'<p><img src={get_reset_image()}></img> Reset/home plot axes to data.</p>'
                          f'<p><img src={get_hover_tool_image()}></img>Toggle mouse hover interaction to videos/images.</p>'
                          )

        button_code = ''
        button_code_media = f"""
        const imageIds = {ids};
        const texts = {text};

        for (let i = 0; i < imageIds.length; i++) {{
            const imgElement = document.getElementById(imageIds[i]);
            const parentDiv = imgElement.parentElement;
            if (parentDiv) {{
                const overlayText = parentDiv.querySelector('.overlay-text');
                if (overlayText) {{
                    // If the overlay text exists, remove it
                    overlayText.remove();
                }} else {{
                    // If the overlay text doesn't exist, add it
                    parentDiv.style.position = 'relative';
                    const overlayDiv = document.createElement('div');
                    overlayDiv.className = 'overlay-text';
                    overlayDiv.style.position = 'absolute';
                    overlayDiv.style.width = '100%';
                    overlayDiv.style.height = '100%';
                    overlayDiv.style.display = 'flex';
                    overlayDiv.style.flexDirection = 'column';
                    overlayDiv.style.alignItems = 'center';
                    overlayDiv.style.justifyContent = 'center';
                    overlayDiv.style.textAlign = 'center';
                    overlayDiv.style.fontWeight = 'bold';
                    overlayDiv.style.fontSize = '22px';
                    overlayDiv.style.backgroundColor = 'rgba(144, 238, 144, {background_alpha})';
                    overlayDiv.innerHTML = texts[i];
                    parentDiv.appendChild(overlayDiv);
                }}
            }}
        }}
        """
        button_code_scatter = f"""
        // code for the scatter plot legend        
        const canvasElement = document.querySelector('.bk-canvas-events');
        const parentOfCanvas = canvasElement.parentElement;
        const overlay = parentOfCanvas.querySelector('.overlay-text');
        
        if (overlay) {{
            overlay.remove();
        }} else {{
            const overlayDiv = document.createElement('div');
            overlayDiv.className = 'overlay-text';
            overlayDiv.style.pointerEvents = 'none';
            overlayDiv.style.position = 'absolute';
            overlayDiv.style.top = '0';
            overlayDiv.style.left = '0';
            overlayDiv.style.width = '100%';
            overlayDiv.style.height = '100%';
            overlayDiv.style.display = 'flex';
            overlayDiv.style.flexDirection = 'column';
            overlayDiv.style.alignItems = 'center';
            overlayDiv.style.justifyContent = 'center';
            overlayDiv.style.textAlign = 'center';
            overlayDiv.style.fontWeight = 'bold';
            overlayDiv.style.fontSize = '22px';
            overlayDiv.style.backgroundColor = 'rgba(144, 238, 144, {background_alpha})';
            overlayDiv.innerHTML = '{legend_scatter}';
            parentOfCanvas.style.position = 'relative';
            parentOfCanvas.appendChild(overlayDiv);
        }}
        """

        button_code_slider = f"""
        const sliderElement = document.querySelector('.unique-slider-class');
        const sliderRect = sliderElement.getBoundingClientRect();
        const sliderOverlay = document.body.querySelector('.overlay-text-slider');

        if (sliderOverlay) {{
            sliderOverlay.remove();
        }} else {{
            const overlayDiv = document.createElement('div');
            overlayDiv.className = 'overlay-text-slider';
            overlayDiv.style.pointerEvents = 'none';
            overlayDiv.style.position = 'absolute';
            overlayDiv.style.top = sliderRect.top + 'px';
            overlayDiv.style.left = sliderRect.left + 'px';
            overlayDiv.style.width = sliderRect.width + 'px';
            overlayDiv.style.height = sliderRect.height + 'px';
            overlayDiv.style.display = 'flex';
            overlayDiv.style.flexDirection = 'column';
            overlayDiv.style.alignItems = 'center';
            overlayDiv.style.justifyContent = 'center';
            overlayDiv.style.textAlign = 'center';
            overlayDiv.style.fontWeight = 'inherit';
            overlayDiv.style.fontFamily = "'Lato', 'Helvetica Neue', Helvetica, Arial, sans-serif";  
            overlayDiv.style.fontSize = '18px';
            overlayDiv.style.backgroundColor = 'rgba(144, 238, 144, {background_alpha})';
            overlayDiv.innerHTML = '<b>Row Slider</b>Hint: Click on the slider and use the arrow keys (left/right) explore the data quickly.';
            overlayDiv.style.zIndex = 1000;  // Ensure it's on top
            document.body.appendChild(overlayDiv);
        }}
        """


        button_code_selection = f"""
        const dropDownElement = document.querySelector('.dropdown_controls');
        const rect = dropDownElement.getBoundingClientRect();
        const dropDownOverlay = document.body.querySelector('.overlay-dropdown');

        if (dropDownOverlay) {{
            dropDownOverlay.remove();
        }} else {{
            const overlayDiv = document.createElement('div');
            overlayDiv.className = 'overlay-dropdown';
            overlayDiv.style.pointerEvents = 'none';
            overlayDiv.style.position = 'absolute';
            overlayDiv.style.top = rect.top + 'px';
            overlayDiv.style.left = rect.left + 'px';
            overlayDiv.style.width = rect.width + 'px';
            overlayDiv.style.height = rect.height + 'px';
            overlayDiv.style.display = 'flex';
            overlayDiv.style.flexDirection = 'column';
            overlayDiv.style.alignItems = 'center';
            overlayDiv.style.justifyContent = 'center';
            overlayDiv.style.textAlign = 'center';
            overlayDiv.style.fontWeight = 'bold';
            overlayDiv.style.fontFamily = "'Lato', 'Helvetica Neue', Helvetica, Arial, sans-serif";  
            overlayDiv.style.fontSize = '18px';
            overlayDiv.style.backgroundColor = 'rgba(144, 238, 144, {background_alpha})';
            overlayDiv.innerHTML = 'Change Axes.';
            overlayDiv.style.zIndex = 1000;  // Ensure it's on top
            document.body.appendChild(overlayDiv);
        }}
        """

        button_code_text_hover = f"""
        const textHoverElement = document.querySelector('.text_hover_display');
        const textHoverRect = textHoverElement.getBoundingClientRect();
        const textHoverOverlay = document.body.querySelector('.overlay-text-hover');

        if (textHoverOverlay) {{
            textHoverOverlay.remove();
        }} else {{
            const overlayDiv = document.createElement('div');
            overlayDiv.className = 'overlay-text-hover';
            overlayDiv.style.pointerEvents = 'none';
            overlayDiv.style.position = 'absolute';
            overlayDiv.style.top = textHoverRect.top + 'px';
            overlayDiv.style.left = textHoverRect.left + 'px';
            overlayDiv.style.width = textHoverRect.width + 'px';
            overlayDiv.style.height = textHoverRect.height + 'px';
            overlayDiv.style.display = 'flex';
            overlayDiv.style.flexDirection = 'column';
            overlayDiv.style.alignItems = 'center';
            overlayDiv.style.justifyContent = 'center';
            overlayDiv.style.textAlign = 'center';
            overlayDiv.style.fontWeight = 'bold';
            overlayDiv.style.fontFamily = "'Lato', 'Helvetica Neue', Helvetica, Arial, sans-serif";  
            overlayDiv.style.fontSize = '24px';
            overlayDiv.style.backgroundColor = 'rgba(144, 238, 144, {background_alpha})';
            overlayDiv.innerHTML = 'Additional data on selected/hovered-on scatter point.';
            overlayDiv.style.zIndex = 1000;  // Ensure it's on top
            document.body.appendChild(overlayDiv);
        }}
        """

        button_code += button_code_media + button_code_scatter + button_code_slider + button_code_selection + button_code_text_hover
        self.toggleLegendButton.js_on_click(CustomJS(code=button_code))

        return self.toggleLegendButton

    def add_slider(self):
        if self.dataset_selector is not None:
            raise RuntimeError("Please add the dataset selector after adding the row slider.")
        # prerequisites: all videos/image/text elements have to be registered
        if len(self.df) == 1:
            warnings.warn("Warning: only one data point, slider will not be shown.")
            # return dummywidget
            return Div(text="")
        self.manual_id_selection_slider = Slider(start=0, end=len(self.df) - 1, value=0, step=1, title="Row",
                                                 name='id_slider',
                                                 width=self.scatter_width + self.scatterplot_select_options_width)
        self.manual_id_selection_slider.css_classes = ["unique-slider-class"]

        hint_div = Div(
            text=(
                "<b>Hint:</b> After clicking on the slider, you may use arrow keys (←/→) to navigate rows."
            )
        )

        self.row_refresh_js = ""
        for registered_video_element in self.registered_video_elements:
            self.row_refresh_js += registered_video_element['js_update']
        for registered_image_element in self.registered_image_elements:
            self.row_refresh_js += registered_image_element['js_update']
        for registered_text_element in self.registered_text_elements:
            self.row_refresh_js += registered_text_element['js_update']

        self.row_refresh_js += 'highlight_df.data["highlight_x"][0] = source.data["active_axis_x"][index];\n'
        self.row_refresh_js += 'highlight_df.data["highlight_y"][0] = source.data["active_axis_y"][index];\n'
        self.row_refresh_js += 'highlight_df.data["last_selected_index"][0] = index;\n'
        self.row_refresh_js += 'highlight_df.change.emit();\n'
        self.row_refresh_js += "source.change.emit();\n"
        # Trigger video re-synchronisation after all sources have been updated
        self.row_refresh_js += "if (window._vSync) { window._vSync = {r: new Set(), ok: false}; }\n"
        callback_slider = "const index = manual_id_selection.value;\n" + self.row_refresh_js

        callback = CustomJS(
            args=dict(source=self.csd_source, manual_id_selection=self.manual_id_selection_slider,
                      highlight_df=self.highlight_csd_source),
            code=callback_slider)

        self.manual_id_selection_slider.js_on_change('value', callback)
        return column([hint_div, self.manual_id_selection_slider])

    def add_video_hover(self, key, width=300, height=300, video_width=None, video_height=None, legend_text="",
                        title=None, autoplay=True):
        if self.dataset_selector is not None:
            raise RuntimeError("Please add the dataset selector after adding video hovers.")
        self._require_scatter_figure()
        # deprecated: video_width & video_height, use width & height instead
        if video_width is not None:
            width = video_width
            logging.warning("video_width is deprecated, use width instead")
        if video_height is not None:
            logging.warning("video_height is deprecated, use height instead")
            height = video_height

        self._remember_media_key(key)
        self._prepare_video_column(key)

        unique_html_id = uuid.uuid4()
        video_update_js = (f'    document.getElementById("{unique_html_id}").src = encodeURI(source.data["{key}"][index].replace(/\\\\/g, "/")).replace(/#/g, "%23");\n'
                           f'    document.getElementById("{unique_html_id}").setAttribute("data-value", index);\n')
        div_video, JS_code = video_html_and_callback(unique_html_id=unique_html_id,
                                                     df=self.df, key=key,
                                                     video_width=width, video_height=height,
                                                     title=title, autoplay=autoplay)
        self.registered_video_elements.append({
            'id': unique_html_id,
            'key': key,
            'legend_text': legend_text,
            'div': div_video,
            'width': width,
            'height': height,
            'title': title,
            'autoplay': autoplay,
            'js_update': video_update_js,
        })

        video_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_video),
                                     code=JS_code)

        video_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        video_hover_tool.callback = video_JS_callback

        self.scatter_figure.add_tools(video_hover_tool)

        return div_video

    def add_stacked_video_hover(self, keys, stack="column", width=300, height=300, video_width=None,
                                video_height=None, legend_text="", title=None, autoplay=True,
                                encoding="h264", ffmpeg_crf=None, ffmpeg_preset=None, ffmpeg_options=None):
        if self.dataset_selector is not None:
            raise RuntimeError("Please add the dataset selector after adding stacked video hovers.")
        self._require_scatter_figure()

        if isinstance(keys, str):
            raise TypeError("keys must be a sequence of dataframe columns, not a single string.")

        keys = list(keys)
        if len(keys) < 2:
            raise ValueError("Please provide at least two video keys to stack.")
        if stack not in ("column", "row"):
            raise ValueError("stack must be either 'column' or 'row'.")

        for key in keys:
            if key not in self.df.columns:
                raise KeyError(f"Could not find video key '{key}' in the dataframe.")
            self._remember_media_key(key)

        stacked_key = f'_stacked_video_{uuid.uuid4().hex}'
        self.generated_media_keys.add(stacked_key)
        self.stacked_video_specs[stacked_key] = {
            'key': stacked_key,
            'keys': keys,
            'stack': stack,
            'encoding': encoding,
            'ffmpeg_crf': ffmpeg_crf,
            'ffmpeg_preset': ffmpeg_preset,
            'ffmpeg_options': None if ffmpeg_options is None else dict(ffmpeg_options),
        }
        self._materialize_stacked_video_column(stacked_key)

        return self.add_video_hover(
            key=stacked_key,
            width=width,
            height=height,
            video_width=video_width,
            video_height=video_height,
            legend_text=legend_text,
            title=title,
            autoplay=autoplay,
        )

    def create_hover_text(self, df_keys_to_show=None, width=500, height=300, container_width=None, container_height=None,
                          remove_path_keys=True, ignore_keys=None):
        if self.dataset_selector is not None:
            raise RuntimeError("Please add the dataset selector after adding hover text.")
        self._require_scatter_figure()
        # deprecated: container_width & container_height, use width & height instead
        if container_width is not None:
            width = container_width
            logging.warning("container_width is deprecated, use width instead")
        if container_height is not None:
            logging.warning("container_height is deprecated, use height instead")
            height = container_height

        unique_html_id = uuid.uuid4()

        df_keys_to_ignore = None
        if remove_path_keys:
            df_keys_to_ignore = self.path_keys

        # TODO: sanity check that keys exist
        if ignore_keys is not None:
            # make sure it is a list
            if isinstance(ignore_keys, str):
                ignore_keys = [ignore_keys]
            df_keys_to_ignore += ignore_keys


        div_text, code_text, js_update_str = text_html_and_callback(unique_id=unique_html_id,
                                                                    df=self.df, df_keys_to_show=df_keys_to_show,
                                                                    df_keys_to_ignore=df_keys_to_ignore,
                                                                    width=width,
                                                                    height=height,
                                                                    float_precision=self.scatter_data_hover_float_precision)

        div_text.css_classes = ["text_hover_display"]


        self.registered_text_elements.append({
            'id': unique_html_id,
            'js_update': js_update_str,
            'div': div_text,
            'df_keys_to_show': None if df_keys_to_show is None else list(df_keys_to_show),
            'df_keys_to_ignore': None if df_keys_to_ignore is None else list(df_keys_to_ignore),
            'width': width,
            'height': height,
        })

        callback_text = CustomJS(args=dict(source=self.csd_source, div=div_text),
                                 code=code_text)

        hover_text = HoverTool(tooltips=None, names=['main_graph'])
        hover_text.callback = callback_text
        self.scatter_figure.add_tools(hover_text)

        return div_text

    def add_dataset_selector(self, datasets, default_dataset=None):
        self._require_scatter_figure()
        if self.dataset_selector is not None:
            raise RuntimeError("A dataset selector has already been added.")
        if not hasattr(self, 'scatterplot_select_options'):
            raise RuntimeError("Please call 'create_scatter_figure()' before adding the dataset selector.")

        try:
            dataset_items = list(datasets.items())
        except AttributeError as exc:
            raise TypeError("datasets must be a mapping of dataset label to pandas DataFrame.") from exc

        if len(dataset_items) < 2:
            raise ValueError("Please provide at least two named datasets.")

        reference_columns = None
        for dataset_label, dataset_df in dataset_items:
            if not isinstance(dataset_df, pd.DataFrame):
                raise TypeError(f"Dataset '{dataset_label}' must be a pandas DataFrame.")
            if dataset_df.empty:
                raise ValueError(f"Dataset '{dataset_label}' is empty. Empty datasets are not supported.")
            if reference_columns is None:
                reference_columns = list(dataset_df.columns)
            elif list(dataset_df.columns) != reference_columns:
                raise ValueError("All datasets must have the same columns and column order.")

        if default_dataset is None:
            default_dataset = dataset_items[0][0]
        if default_dataset not in dict(dataset_items):
            raise ValueError(f"Default dataset '{default_dataset}' was not found in datasets.")

        live_df = self.df
        live_source = self.csd_source
        live_view = self.csd_view

        dataset_sources = []
        dataset_labels = []
        dataset_legend_items = []

        for dataset_label, dataset_df in dataset_items:
            self.df = dataset_df.copy()
            self.initialize_data()
            prepared_media_keys = set()

            for path_key in self.path_keys:
                self._prepare_media_key_for_dataset(path_key, prepared_media_keys=prepared_media_keys)

            legend_items = []
            if self.scatter_legend is not None and self.main_scatter_renderer is not None and 'legend' in self.df.columns:
                first_index_by_label = {}
                for row_index, legend_label in enumerate(self.df['legend'].tolist()):
                    if legend_label not in first_index_by_label:
                        first_index_by_label[legend_label] = row_index
                for legend_label, row_index in first_index_by_label.items():
                    legend_items.append(LegendItem(
                        label={'value': str(legend_label)},
                        renderers=[self.main_scatter_renderer],
                        index=row_index,
                    ))

            dataset_labels.append(dataset_label)
            dataset_sources.append(self.csd_source)
            dataset_legend_items.append(legend_items)

        self.df = live_df
        self.csd_source = live_source
        self.csd_view = live_view
        self.dataset_labels = dataset_labels
        self.dataset_sources = dataset_sources
        self.dataset_legend_items = dataset_legend_items

        refresh_row_js = self.row_refresh_js
        if refresh_row_js is None:
            refresh_row_js = ""
            for registered_video_element in self.registered_video_elements:
                refresh_row_js += registered_video_element['js_update']
            for registered_image_element in self.registered_image_elements:
                refresh_row_js += registered_image_element['js_update']
            for registered_text_element in self.registered_text_elements:
                refresh_row_js += registered_text_element['js_update']
            refresh_row_js += 'highlight_df.data["highlight_x"][0] = source.data["active_axis_x"][index];\n'
            refresh_row_js += 'highlight_df.data["highlight_y"][0] = source.data["active_axis_y"][index];\n'
            refresh_row_js += 'highlight_df.data["last_selected_index"][0] = index;\n'
            refresh_row_js += 'highlight_df.change.emit();\n'
            refresh_row_js += "source.change.emit();\n"
            refresh_row_js += "if (window._vSync) { window._vSync = {r: new Set(), ok: false}; }\n"

        selector_args = dict(
            source=self.csd_source,
            highlight_df=self.highlight_csd_source,
            dataset_selector=None,
            dataset_labels=self.dataset_labels,
            dataset_sources=self.dataset_sources,
            axesselect_x=self.axesselect_x,
            axesselect_y=self.axesselect_y,
        )
        if self.scatter_legend is not None:
            selector_args['legend'] = self.scatter_legend
            selector_args['dataset_legend_items'] = self.dataset_legend_items
        if hasattr(self, 'manual_id_selection_slider'):
            selector_args['manual_id_selection'] = self.manual_id_selection_slider

        selector_code = """
        const dataset_index = dataset_labels.indexOf(dataset_selector.value);
        const selected_source = dataset_sources[dataset_index];
        const new_data = {};
        for (const [key, value] of Object.entries(selected_source.data)) {
            new_data[key] = value.slice ? value.slice() : value;
        }
        source.data = new_data;
        source.data['active_axis_x'] = source.data[axesselect_x.value];
        source.data['active_axis_y'] = source.data[axesselect_y.value];
        """
        if self.scatter_legend is not None:
            selector_code += """
        const selected_legend_items = dataset_legend_items[dataset_index];
        legend.items = selected_legend_items;
        legend.visible = selected_legend_items.length > 0;
        legend.change.emit();
        """
        if hasattr(self, 'manual_id_selection_slider'):
            selector_code += """
        const row_count = source.data["active_axis_x"].length;
        manual_id_selection.start = 0;
        manual_id_selection.end = Math.max(row_count - 1, 0);
        manual_id_selection.value = 0;
        """
        selector_code += "const index = 0;\n" + refresh_row_js

        self.dataset_selector = Select(
            title="Dataset:",
            value=default_dataset,
            options=self.dataset_labels,
            width=self.scatterplot_select_options_width,
        )
        selector_args['dataset_selector'] = self.dataset_selector
        self.dataset_selector.js_on_change('value', CustomJS(args=selector_args, code=selector_code))
        self.scatterplot_select_options.children = [self.dataset_selector] + list(self.scatterplot_select_options.children)

        default_source = self.dataset_sources[self.dataset_labels.index(default_dataset)]
        self.csd_source.data = {
            key: value.copy() if hasattr(value, 'copy') else value
            for key, value in default_source.data.items()
        }
        if self.scatter_legend is not None:
            default_legend_items = self.dataset_legend_items[self.dataset_labels.index(default_dataset)]
            self.scatter_legend.items = default_legend_items
            self.scatter_legend.visible = len(default_legend_items) > 0
        self.df = pd.DataFrame(self.csd_source.data)
        self.highlight_csd_source.data = {
            'highlight_x': [self.csd_source.data['active_axis_x'][0]],
            'highlight_y': [self.csd_source.data['active_axis_y'][0]],
            'last_selected_index': [0],
        }

        if hasattr(self, 'manual_id_selection_slider'):
            self.manual_id_selection_slider.start = 0
            self.manual_id_selection_slider.end = len(self.df) - 1
            self.manual_id_selection_slider.value = 0

        for registered_image_element in self.registered_image_elements:
            image_div, _ = image_html_and_callback(
                unique_html_id=registered_image_element['id'],
                df=self.df,
                key=registered_image_element['key'],
                height=registered_image_element['height'],
                width=registered_image_element['width'],
                title=registered_image_element['title'],
            )
            registered_image_element['div'].text = image_div.text

        for registered_video_element in self.registered_video_elements:
            video_div, _ = video_html_and_callback(
                unique_html_id=registered_video_element['id'],
                df=self.df,
                key=registered_video_element['key'],
                video_width=registered_video_element['width'],
                video_height=registered_video_element['height'],
                title=registered_video_element['title'],
                autoplay=registered_video_element['autoplay'],
            )
            registered_video_element['div'].text = video_div.text

        for registered_text_element in self.registered_text_elements:
            text_div, _, _ = text_html_and_callback(
                unique_id=registered_text_element['id'],
                df=self.df,
                df_keys_to_show=registered_text_element['df_keys_to_show'],
                df_keys_to_ignore=registered_text_element['df_keys_to_ignore'],
                width=registered_text_element['width'],
                height=registered_text_element['height'],
                float_precision=self.scatter_data_hover_float_precision,
            )
            registered_text_element['div'].text = text_div.text

        return self.dataset_selector
