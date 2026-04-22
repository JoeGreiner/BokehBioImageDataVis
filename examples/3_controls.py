# Default axes of the scatter plot, a row slider, a legend button, and a global video toggle button.


import pandas as pd

from BokehBioImageDataVis.src.utils import download_files_simple_example_1

download_files_simple_example_1()

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis
from bokeh.layouts import column, row

data = pd.DataFrame({
    'x1': [1, 2, 3],
    'x2': [1, 4, 16],
    'x3': [1, 8, 64],
    'animal': ['cat', 'dog', 'dog'],
    'path_to_images': ['data/pictures/cat1.jpg',
                       'data/pictures/dog1.jpg',
                       'data/pictures/dog2.jpg'],
    'path_to_videos': ['data/videos/cat1.mp4',
                       'data/videos/dog1.mp4',
                       'data/videos/dog2.mp4'],
})

bokeh_fig = BokehBioImageDataVis(
    data,
    output_filename='example_3_controls/vis.html',
    category_key='animal',
    legend_position='top_left',
    x_axis_key='x3',
    y_axis_key='x2',
)

scatter_plot = bokeh_fig.create_scatter_figure()

img_hover = bokeh_fig.add_image_hover(
    key='path_to_images',
    title='animal picture',
    legend_text='<span style="color:red">animal picture</span>',
)

vid_hover = bokeh_fig.add_video_hover(
    key='path_to_videos',
    title='animal video',
    autoplay=True,
    legend_text='<span style="color:green">animal video</span>',
)

text_hover = bokeh_fig.create_hover_text(ignore_keys=['color_mapping'])
row_slider = bokeh_fig.add_slider()
legend_button = bokeh_fig.add_legend()
video_toggle_button = bokeh_fig.add_toggle_video_button()

bokeh_fig.show_bokeh(
    row([
        column([row([legend_button, video_toggle_button]), row_slider, scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
    ])
)
