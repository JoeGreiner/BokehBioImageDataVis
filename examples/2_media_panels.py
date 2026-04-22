# Image and video panels scaling, custom media titles, and filtered text output.

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

bokeh_fig = BokehBioImageDataVis(data, output_filename='example_2_media_panels/vis.html')
scatter_plot = bokeh_fig.create_scatter_figure()

obj_width = 400
obj_height = 400
img_hover = bokeh_fig.add_image_hover(
    key='path_to_images',
    width=obj_width,
    height=obj_height,
    title='animal picture',
)

vid_hover = bokeh_fig.add_video_hover(
    key='path_to_videos',
    width=obj_width,
    height=obj_height,
    title='animal video',
    autoplay=True,
)

duplicate_vid_hover = bokeh_fig.add_video_hover(
    key='path_to_videos',
    width=obj_width,
    height=obj_height,
    title='animal video (second panel)',
    autoplay=True,
)

text_hover = bokeh_fig.create_hover_text(ignore_keys=['x2'])

bokeh_fig.show_bokeh(
    row([
        column([scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
        duplicate_vid_hover,
    ])
)
