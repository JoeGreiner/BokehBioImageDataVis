import os.path
import shutil
import uuid
from os.path import join
import pandas as pd
from bokeh.io import show, output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, CDSView, Select, CustomJS, HoverTool, LayoutDOM, Slider, Button, Div
from bokeh.palettes import Category10, Category20
from bokeh.plotting import figure
import logging

from BokehBioImageDataVis.src.bokeh_helpers.get_bokeh_images_base64 import get_pan_tool_image, get_rect_zoom_image, \
    get_mouse_wheel_image, get_reset_image, get_hover_tool_image
from BokehBioImageDataVis.src.colormapping import random_color
from BokehBioImageDataVis.src.file_handling import copy_files_to_output_dir, create_file
from BokehBioImageDataVis.src.html_snippets import image_html_and_callback, text_html_and_callback, \
    video_html_and_callback
from BokehBioImageDataVis.src.utils import identify_numerical_variables


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
                 clearOutputFolderIfNotEmpty=False,
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
        :param output_filename: html output filename
        :param output_title: title of the html output
        '''
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')



        self.df = df
        if add_id_to_dataframe:
            logging.info('Adding id column to dataframe')
            # check if id is already present
            if 'id' in self.df.columns:
                logging.warning('Can insert id into dataframe, as it is already present!')
            else:
                self.df.insert(0, 'id', range(0, len(self.df)))  # can be used with the slider

        if category_key:
            logging.info(f'Category key: {category_key}')
            self.category_key = category_key
        else:
            self.category_key = None

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
        self.numeric_options = identify_numerical_variables(self.df)

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
            # change legend background alpha
            self.scatter_figure.legend.background_fill_alpha = 0.5
            # show the title of the legend
            self.scatter_figure.legend.title = self.category_key
        elif colorKey and colorLegendKey:
            logging.info(f'Using {colorKey} as color key and {colorLegendKey} for legend.')
            self.scatter_figure.circle('active_axis_x', 'active_axis_y',
                                       source=self.csd_source, view=self.csd_view,
                                       size=self.scatter_size,
                                       alpha=scatter_alpha,
                                       color=colorKey, legend_group=colorLegendKey, name='main_graph'
                                       )
            # change legend location to bottom right
            self.scatter_figure.legend.location = "bottom_right"
            # change legend background alpha
            self.scatter_figure.legend.background_fill_alpha = 0.5
            # show the title of the legend
            self.scatter_figure.legend.title = self.category_key
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
        self.scatterplot_select_options.css_classes = ["dropdown_controls"]

        return row([self.scatterplot_select_options, self.scatter_figure])

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

    def add_image_hover(self, key, height=300, width=300, image_width=None, image_height=None, legend_text="",):
        # deprecated: image_width and image_height are not used anymore
        if image_width is not None:
            width = image_width
            logging.warning("image_width is deprecated and not used anymore. Use width instead")
        if image_height is not None:
            height = image_height
            logging.warning("image_height is deprecated and not used anymore. Use height instead")

        self.non_data_keys.append(key)
        self.path_keys.append(key)

        if self.do_copy_files_to_output_dir:
            self.df, self.used_paths = copy_files_to_output_dir(df=self.df, path_key=key,
                                                                output_folder=self.output_folder,
                                                                used_paths=self.used_paths,
                                                                copy_files_dir_level=self.copy_files_dir_level)
            self.csd_source.data[key] = self.df[key]

        unique_html_id = uuid.uuid4()
        self.registered_image_elements.append({'id': unique_html_id, 'key': key, 'legend_text': legend_text})
        div_img, callback_img = image_html_and_callback(unique_html_id=unique_html_id,
                                                        df=self.df, key=key,
                                                        height=height, width=width)

        img_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_img),
                                   code=callback_img)

        img_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        img_hover_tool.callback = img_JS_callback

        self.scatter_figure.add_tools(img_hover_tool)

        return div_img

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

        self.toggleLegendButton = Button(label="Show Legend", button_type="success",
                                         css_classes=["highlight-button"])
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
            overlayDiv.innerHTML = '<b>Id Slider</b>Hint: Click on the slider and use the arrow keys (left/right) explore the data quickly.';
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
        # prerequisites: all videos/image/text elements have to be registered
        self.manual_id_selection_slider = Slider(start=0, end=len(self.df) - 1, value=0, step=1, title="Id", name='id_slider')
        self.manual_id_selection_slider.css_classes = ["unique-slider-class"]

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

    def add_video_hover(self, key, width=300, height=300, video_width=None, video_height=None, legend_text=""):
        # deprecated: video_width & video_height, use width & height instead
        if video_width is not None:
            width = video_width
            logging.warning("video_width is deprecated, use width instead")
        if video_height is not None:
            logging.warning("video_height is deprecated, use height instead")
            height = video_height


        self.non_data_keys.append(key)
        self.path_keys.append(key)

        if self.do_copy_files_to_output_dir:
            self.df, self.used_paths = copy_files_to_output_dir(df=self.df, path_key=key,
                                                                output_folder=self.output_folder,
                                                                used_paths=self.used_paths,
                                                                copy_files_dir_level=self.copy_files_dir_level)
            self.csd_source.data[key] = self.df[key]

        unique_html_id = uuid.uuid4()
        self.registered_video_elements.append({'id': unique_html_id, 'key': key, 'legend_text': legend_text})
        div_video, JS_code = video_html_and_callback(unique_html_id=unique_html_id,
                                                     df=self.df, key=key,
                                                     video_width=width, video_height=height)

        video_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_video),
                                     code=JS_code)

        video_hover_tool = HoverTool(tooltips=None, names=['main_graph'])
        video_hover_tool.callback = video_JS_callback

        self.scatter_figure.add_tools(video_hover_tool)

        return div_video

    def create_hover_text(self, df_keys_to_show=None, width=500, height=300, container_width=None, container_height=None,
                          remove_path_keys=True, ignore_keys=None):
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


        self.registered_text_elements.append({'id': unique_html_id, 'js_update': js_update_str})

        callback_text = CustomJS(args=dict(source=self.csd_source, div=div_text),
                                 code=code_text)

        hover_text = HoverTool(tooltips=None, names=['main_graph'])
        hover_text.callback = callback_text
        self.scatter_figure.add_tools(hover_text)

        return div_text
