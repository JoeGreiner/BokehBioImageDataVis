import uuid

import numpy as np
from bokeh.io import show, output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, CDSView, Select, CustomJS, Div, HoverTool, LayoutDOM
from bokeh.plotting import figure

from pandas.api.types import is_numeric_dtype
from pandas.core.dtypes.common import is_integer_dtype, is_float_dtype

from typing import TYPE_CHECKING, Any


class BokehBioImageDataVis:
    def __init__(self, df,
                 scatter_width=600, scatter_height=600, scatter_size=10,
                 do_scatter_data_hover=True,
                 scatter_data_hover_float_precision=2,
                 output_filename='BokehBioImageDataVis.html',
                 output_title='BokehBioImageDataVis', ):
        self.df = df

        self.scatter_width = scatter_width
        self.scatter_height = scatter_height
        self.scatter_size = scatter_size
        self.do_scatter_data_hover = do_scatter_data_hover
        self.scatter_data_hover_float_precision = scatter_data_hover_float_precision

        self.non_data_keys = []

        output_file(output_filename, title=output_title)

        self.initialize_data()
        self.create_scatter_figure()

    def show_bokeh(self, obj: LayoutDOM):
        self.scatter_figure.toolbar_location = None
        show(obj)

    def initialize_data(self):
        self.identify_numerical_variables()
        self.df['active_axis_x'] = self.df[self.numeric_options[0]]
        self.df['active_axis_y'] = self.df[self.numeric_options[1]]

        self.csd_source = ColumnDataSource(data=self.df)
        self.csd_view = CDSView(source=self.csd_source)

    def create_scatter_figure(self):
        self.scatter_figure = figure(plot_height=self.scatter_height,
                                     plot_width=self.scatter_width,
                                     x_axis_label=self.numeric_options[0],
                                     y_axis_label=self.numeric_options[1])

        self.scatter_figure.circle('active_axis_x', 'active_axis_y',
                                   source=self.csd_source, view=self.csd_view,
                                   size=self.scatter_size,
                                   # color="colors", legend_group='id'
                                   )

        self.axesselect_x = Select(title="X-Axis:", value=self.numeric_options[0], options=self.numeric_options)
        self.axesselect_x.js_on_change('value',
                                       CustomJS(args=dict(source=self.csd_source,
                                                          axesselect_x=self.axesselect_x,
                                                          xaxis=self.scatter_figure.xaxis[0]),
                                                code="""
          source.data['active_axis_x'] = source.data[axesselect_x.value]
          source.change.emit()
          xaxis.axis_label = axesselect_x.value
          """))

        self.axesselect_y = Select(title="Y-Axis:", value=self.numeric_options[1], options=self.numeric_options)
        self.axesselect_y.js_on_change('value',
                                       CustomJS(args=dict(source=self.csd_source,
                                                          axesselect_y=self.axesselect_y,
                                                          yaxis=self.scatter_figure.yaxis[0]),
                                                code="""
          source.data['active_axis_y'] = source.data[axesselect_y.value]
          source.change.emit()
          yaxis.axis_label = axesselect_y.value
          """))

        controls = [self.axesselect_x, self.axesselect_y]
        self.scatterplot_select_options = column(*controls, width=100)

        return row([self.scatterplot_select_options, self.scatter_figure])

    def identify_numerical_variables(self):
        self.numeric_options = []
        for key in list(self.df.keys()):
            if is_numeric_dtype(self.df[key]):
                self.numeric_options.append(key)

    def add_image_hover(self, key, image_height=300, image_width=300):
        self.non_data_keys.append(key)

        unique_html_id = uuid.uuid4()
        text_div_html_cell_image = ('<img\n'
                                    f'    src="" height="{image_height}"\n'
                                    f'    id="{unique_html_id}"\n'
                                    '    style="float: left; margin: 0px 15px 15px 0px;"\n'
                                    '></img>\n'
                                    '')
        div_img = Div(width=image_width, height=image_height, width_policy="fixed",
                      text=text_div_html_cell_image)

        codeHoverCellImage = ("const indices = cb_data.index.indices\n"
                              "if(indices.length > 0){\n"
                              "    const index = indices[0];\n"
                              f'    document.getElementById("{unique_html_id}").src = source.data["{key}"][index];\n'
                              "}")

        img_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_img),
                                   code=codeHoverCellImage)

        img_hover_tool = HoverTool(tooltips=None)
        img_hover_tool.callback = img_JS_callback

        self.scatter_figure.add_tools(img_hover_tool)

        return div_img

    def add_video_hover(self, key, video_width=300):
        self.non_data_keys.append(key)

        unique_html_id = uuid.uuid4()

        text_div_videos = ('<div style="clear:left; float: left; margin: 0px 15px 15px 0px;";>\n'
                           f'    <video width="{video_width}" controls autoplay muted loop id="{unique_html_id}" data-value="firstvalue">\n'
                           '    <source src="" type="video/mp4">\n'
                           '    Your browser does not support the video tag.\n'
                           '</div>\n')

        div_video = Div(width=video_width, width_policy="fixed",
                        text=text_div_videos)

        JS_callback_video = \
            ("const indices = cb_data.index.indices\n"
             "if(indices.length > 0){\n"
             "    const index = indices[0];\n"
             f'    const old_index = document.getElementById("{unique_html_id}").getAttribute("data-value")\n'
             '    if(index != old_index){\n'
             f'        document.getElementById("{unique_html_id}").src = source.data["{key}"][index];\n'
             f'        document.getElementById("{unique_html_id}").setAttribute("data-value", index);\n'
             '   }\n'
             "}")

        video_JS_callback = CustomJS(args=dict(source=self.csd_source, div=div_video),
                                     code=JS_callback_video)

        video_hover_tool = HoverTool(tooltips=None)
        video_hover_tool.callback = video_JS_callback

        self.scatter_figure.add_tools(video_hover_tool)

        return div_video

    def create_hover_text(self):
        prefix = ("const indices = cb_data.index.indices\n"
                  "if(indices.length > 0){\n"
                  "    const index = indices[0];")

        combined_str = ""
        assigment_char = '='
        for key in list(self.df.keys()):
            if key == 'active_axis_x' or key == 'active_axis_y':
                continue
            if key in self.non_data_keys:
                print(f'{key} is non_data.')
                continue
            if is_float_dtype(self.df[key]):
                line = f'    div.text {assigment_char} "{key}:" + " " + source.data["{key}"][index]' \
                       f'.toFixed({self.scatter_data_hover_float_precision}).toString() + "<br>";\n'
            else:
                line = f'    div.text {assigment_char} "{key}:" + " " + source.data["{key}"][index].toString() + "<br>";\n'
            assigment_char = '+='
            combined_str += line

        postfix = "}"

        codeScatterDataHover = f'{prefix}\n{combined_str}\n{postfix}'
        width_stats = 100
        div_text = Div(width=width_stats,
                       height=self.scatter_height - 300, height_policy="fixed",
                       text="""hi""")
        callback_text = CustomJS(args=dict(source=self.csd_source,
                                           div=div_text),
                                 code=codeScatterDataHover)

        hover_text = HoverTool(tooltips=None)
        hover_text.callback = callback_text

        self.scatter_figure.add_tools(hover_text)

        return div_text
