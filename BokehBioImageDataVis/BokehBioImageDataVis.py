import os.path
import uuid
import pandas as pd
from bokeh.io import show, output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, CDSView, Select, CustomJS, Div, HoverTool, LayoutDOM, Slider
from bokeh.palettes import Category10, Category20, Set3
from bokeh.plotting import figure
from pandas.api.types import is_numeric_dtype
from pandas.core.dtypes.common import is_float_dtype
import logging

from BokehBioImageDataVis.src.colormapping import random_color
from BokehBioImageDataVis.src.file_handling import copy_files_to_output_dir


class BokehBioImageDataVis:
    def __init__(self, df,
                 scatter_width=600, scatter_height=600, scatter_size=10,
                 do_scatter_data_hover=True,
                 scatter_data_hover_float_precision=2,
                 x_axis_key=None,
                 y_axis_key=None,
                 category_key=None,
                 dropdown_options=None,
                 add_id_to_dataframe=True,
                 do_copy_files_to_output_dir=True,
                 copy_files_dir_level=1,
                 output_filename='BokehBioImageDataVis.html',
                 output_title='BokehBioImageDataVis', ):
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
        :param output_filename: html output filename
        :param output_title: title of the html output
        '''
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

        self.df = df
        if add_id_to_dataframe:
            logging.info('Adding id column to dataframe')
            self.df.insert(0, 'id', range(0, len(self.df)))  # can be used with the slider

        if category_key:
            logging.info(f'Category key: {category_key}')
            self.category_key = category_key

        self.output_folder = os.path.dirname(output_filename)
        if self.output_folder == '':
            self.output_folder = '.'  # current folder
        logging.info(f'Output folder: {self.output_folder}')

        logging.info(f'Output filename: {output_filename}')
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # holds tuples of [dataframe_key and html unique ideas]
        self.registered_video_elements = []
        self.registered_image_elements = []

        # touple of id and update function
        self.registered_text_elements = []

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

        self.non_data_keys = []
        self.path_keys = []
        self.identify_numerical_variables()
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
        self.do_scatter_data_hover = do_scatter_data_hover
        self.scatter_data_hover_float_precision = scatter_data_hover_float_precision

        output_file(output_filename, title=output_title, mode="inline")

        self.initialize_data()
        self.initialize_highlighter()

    def show_bokeh(self, obj: LayoutDOM):
        # self.scatter_figure.toolbar_location = None
        self.add_hover_highlight()
        show(obj)
        self.make_unzip_me_file()

    def initialize_data(self):
        self.df['active_axis_x'] = self.df[self.x_axis_key]
        self.df['active_axis_y'] = self.df[self.y_axis_key]

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
        self.highlight_df = pd.DataFrame({'highlight_x': [self.df['active_axis_x'][init_index]],
                                          'highlight_y': [self.df['active_axis_y'][init_index]],
                                          'last_selected_index': [0]})

        self.highlight_csd_source = ColumnDataSource(data=self.highlight_df)
        self.highlight_csd_view = CDSView(source=self.highlight_csd_source)

    def create_scatter_figure(self, colorKey=None, colorLegendKey=None, scatter_alpha=0.5, highlight_alpha=0.3):

        self.scatter_figure = figure(plot_height=self.scatter_height,
                                     plot_width=self.scatter_width,
                                     x_axis_label=self.x_axis_key,
                                     y_axis_label=self.y_axis_key,
                                     tools="pan,wheel_zoom,box_zoom,reset")

        self.scatter_figure.circle('highlight_x', 'highlight_y',
                                   source=self.highlight_csd_source, view=self.highlight_csd_view,
                                   size=3 * self.scatter_size, color="red", alpha=highlight_alpha
                                   )
        if self.category_key:
            logging.info(f'Using {self.category_key} as color key.')
            self.scatter_figure.circle('active_axis_x', 'active_axis_y',
                                       source=self.csd_source, view=self.csd_view,
                                       size=self.scatter_size,
                                       alpha=scatter_alpha,
                                       color='color_mapping', legend_group=self.category_key, name='main_graph'
                                       )
            # change legend location to bottom right
            self.scatter_figure.legend.location = "bottom_right"
        elif colorKey and colorLegendKey:
            logging.info(f'Using {colorKey} as color key and {colorLegendKey} for legend.')
            self.scatter_figure.circle('active_axis_x', 'active_axis_y',
                                       source=self.csd_source, view=self.csd_view,
                                       size=self.scatter_size,
                                       alpha=scatter_alpha,
                                       color=colorKey, legend_group=colorLegendKey, name='main_graph'
                                       )
        else:
            self.scatter_figure.circle('active_axis_x', 'active_axis_y',
                                       source=self.csd_source, view=self.csd_view,
                                       size=self.scatter_size, name='main_graph',
                                       alpha=scatter_alpha
                                       # color="colors", legend_group='id'
                                       )

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
        self.scatterplot_select_options = column(*controls, width=100)

        return row([self.scatterplot_select_options, self.scatter_figure])

    def identify_numerical_variables(self):
        self.numeric_options = []
        for key in list(self.df.keys()):
            if is_numeric_dtype(self.df[key]):
                self.numeric_options.append(key)

    def add_hover_highlight(self):

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
            code_hover_highlight += "    manual_id_selection.value = source.data['id'][index];\n"

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

    def add_image_hover(self, key, image_height=300, image_width=300):
        self.non_data_keys.append(key)
        self.path_keys.append(key)

        if self.do_copy_files_to_output_dir:
            self.df, self.used_paths = copy_files_to_output_dir(df=self.df, path_key=key,
                                                                output_folder=self.output_folder,
                                                                used_paths=self.used_paths,
                                                                copy_files_dir_level=self.copy_files_dir_level)
            self.csd_source.data[key] = self.df[key]

        unique_html_id = uuid.uuid4()
        self.registered_image_elements.append({'id': unique_html_id, 'key': key})

        text_div_html_cell_image = ('<img\n'
                                    f'    src="{self.df[key][0]}" height="{image_height}"\n'
                                    f'    id="{unique_html_id}"\n'
                                    '    style="float: left; margin: 0px 15px 15px 0px;"\n'
                                    '></img>\n'
                                    '')
        div_img = Div(width=image_width, height=image_height, width_policy="fixed",
                      text=text_div_html_cell_image)

        codeHoverCellImage = ("const indices = cb_data.index.indices\n"
                              "if(indices.length > 0){\n"
                              "    const index = indices[0];\n"
                              f'   document.getElementById("{unique_html_id}").src = source.data["{key}"][index];\n'
                              "}")

        img_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_img),
                                   code=codeHoverCellImage)

        img_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        img_hover_tool.callback = img_JS_callback

        self.scatter_figure.add_tools(img_hover_tool)

        return div_img

    def add_slider(self):
        # prerequisites: all videos/image/text elements have to be registered
        self.manual_id_selection_slider = Slider(start=0, end=len(self.df) - 1, value=0, step=1, title="Id")

        callback_slider = "const index = manual_id_selection.value;\n"
        for registered_video_element in self.registered_video_elements:
            current_key = registered_video_element['key']
            current_id = registered_video_element['id']
            callback_slider += f'document.getElementById("{current_id}").src = source.data["{current_key}"][index];\n'
        for registered_image_element in self.registered_image_elements:
            current_key = registered_image_element['key']
            current_id = registered_image_element['id']
            callback_slider += f'document.getElementById("{current_id}").src = source.data["{current_key}"][index];\n'
        for registered_text_element in self.registered_text_elements:
            current_update_function = registered_text_element['js_update']
            callback_slider += current_update_function.replace("    ", "")

        callback_slider += f'highlight_df.data["highlight_x"][0] = source.data["active_axis_x"][index];\n'
        callback_slider += f'highlight_df.data["highlight_y"][0] = source.data["active_axis_y"][index];\n'
        callback_slider += f'highlight_df.data["last_selected_index"][0] = index;\n'
        callback_slider += f'highlight_df.change.emit();\n'
        callback_slider += f"source.change.emit();"
        # callback_slider += f"console.log(manual_id_selection.value);"

        callback = CustomJS(
            args=dict(source=self.csd_source, manual_id_selection=self.manual_id_selection_slider,
                      highlight_df=self.highlight_csd_source),
            code=callback_slider)

        self.manual_id_selection_slider.js_on_change('value', callback)
        return self.manual_id_selection_slider

    def add_video_hover(self, key, video_width=300, video_height=300):
        self.non_data_keys.append(key)
        self.path_keys.append(key)

        if self.do_copy_files_to_output_dir:
            self.df, self.used_paths = copy_files_to_output_dir(df=self.df, path_key=key,
                                                                output_folder=self.output_folder,
                                                                used_paths=self.used_paths,
                                                                copy_files_dir_level=self.copy_files_dir_level)
            self.csd_source.data[key] = self.df[key]
        unique_html_id = uuid.uuid4()
        self.registered_video_elements.append({'id': unique_html_id, 'key': key})

        text_div_videos = ('<div style="clear:left; float: left; margin: 0px 15px 15px 0px;";>\n'
                           f'    <video width="{video_width}" controls autoplay muted loop id="{unique_html_id}" data-value="firstvalue">\n'
                           f'    <source src="{self.df[key][0]}" type="video/mp4">\n'
                           f'    Your browser does not support the video tag.\n'
                           '</div>\n')

        div_video = Div(width=video_width, width_policy="fixed", height=video_height,
                        text=text_div_videos)

        JS_callback_video = \
            ("const indices = cb_data.index.indices;\n"
             "if(indices.length > 0){\n"
             "    const index = indices[0];\n"
             f'    const old_index = document.getElementById("{unique_html_id}").getAttribute("data-value");\n'
             '    if(index != old_index){\n'
             f'        document.getElementById("{unique_html_id}").src = source.data["{key}"][index];\n'
             f'        document.getElementById("{unique_html_id}").setAttribute("data-value", index);\n'
             '    }\n'
             "}")

        video_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_video),
                                     code=JS_callback_video)

        video_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        video_hover_tool.callback = video_JS_callback

        self.scatter_figure.add_tools(video_hover_tool)

        return div_video

    def create_hover_text(self, df_keys_to_show=None, container_width=500, container_height=300):
        prefix = ("const indices = cb_data.index.indices;\n"
                  "if(indices.length > 0){\n"
                  "    const index = indices[0];")

        unique_html_id = uuid.uuid4()

        combined_str = ""
        assigment_char = '='
        if df_keys_to_show is None:
            df_keys_to_show = list(self.df.keys())
        for key in df_keys_to_show:
            if key == 'active_axis_x' or key == 'active_axis_y':
                continue
            if key in self.non_data_keys:
                logging.debug(f'{key} is non_data.')
                continue
            if is_float_dtype(self.df[key]):
                line = f'    document.getElementById("{unique_html_id}").innerHTML {assigment_char} "<b>{key}</b>:" + " " + source.data["{key}"][index]' \
                       f'.toFixed({self.scatter_data_hover_float_precision}).toString() + "<br>";\n'
            else:
                line = f'    document.getElementById("{unique_html_id}").innerHTML {assigment_char} "<b>{key}</b>:" + " " + source.data["{key}"][index].toString() + "<br>";\n'
            assigment_char = '+='
            combined_str += line

        self.registered_text_elements.append({'id': unique_html_id, 'js_update': combined_str})

        postfix = "}"

        codeScatterDataHover = f'{prefix}\n{combined_str}\n{postfix}'
        div_text = Div(width=container_width,
                       height=container_height, height_policy="fixed",
                       text=f"<div id='{unique_html_id}' style='clear:left; float: left; margin: 0px 15px 15px 0px;';></div>")

        callback_text = CustomJS(args=dict(source=self.csd_source,
                                           div=div_text),
                                 code=codeScatterDataHover)

        hover_text = HoverTool(tooltips=None, names=['main_graph'])
        hover_text.callback = callback_text
        self.scatter_figure.add_tools(hover_text)

        return div_text

    def make_unzip_me_file(self):
        filename = 'PLEASE_MAKE_SURE_IM_UNZIPPED.txt'

        # create file
        with open(os.path.join(self.output_folder, filename), 'w') as f:
            f.write('Please make sure to unzip the data folder before opening the html file.')
