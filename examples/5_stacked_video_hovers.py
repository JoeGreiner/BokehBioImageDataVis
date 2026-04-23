# Stacked video hovers for grouped fullscreen playback and synchronized comparison.

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
    'path_to_videos': ['data/videos/cat1.mp4',
                       'data/videos/dog1.mp4',
                       'data/videos/dog2.mp4'],
})

bokeh_fig = BokehBioImageDataVis(data, output_filename='example_5_stacked_video_hovers/vis.html')
scatter_plot = bokeh_fig.create_scatter_figure()

stacked_vid_hover = bokeh_fig.add_stacked_video_hover(
    keys=['path_to_videos', 'path_to_videos'],
    stack='column',
    width=400,
    height=400,
    title='stacked animal videos',
    autoplay=True,
)

single_vid_hover = bokeh_fig.add_video_hover(
    key='path_to_videos',
    width=400,
    height=400,
    title='single animal video',
    autoplay=True,
)

text_hover = bokeh_fig.create_hover_text()

bokeh_fig.show_bokeh(
    row([
        column([scatter_plot, text_hover]),
        row([single_vid_hover, stacked_vid_hover]),
    ])
)
