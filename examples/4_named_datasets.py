# Switching between multiple named datasets while keeping the same scatter plot, media panels,
# text panel, and slider layout.
# E.g. when you  want one HTML output that can flip between all samples, filtered subsets, or different cohorts.

import pandas as pd

from BokehBioImageDataVis.src.utils import download_files_simple_example_1

download_files_simple_example_1()

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis
from bokeh.layouts import column, row

all_animals = pd.DataFrame({
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

dog_animals = all_animals[all_animals['animal'] == 'dog'].reset_index(drop=True)
cat_animals = all_animals[all_animals['animal'] == 'cat'].reset_index(drop=True)

bokeh_fig = BokehBioImageDataVis(
    all_animals,
    output_filename='example_4_named_datasets/vis.html',
    category_key='animal',
)

scatter_plot = bokeh_fig.create_scatter_figure()
img_hover = bokeh_fig.add_image_hover(key='path_to_images', title='animal picture')
vid_hover = bokeh_fig.add_video_hover(key='path_to_videos', title='animal video')
text_hover = bokeh_fig.create_hover_text()
row_slider = bokeh_fig.add_slider()

bokeh_fig.add_dataset_selector({
    'All': all_animals,
    'Dogs Only': dog_animals,
    'Cats Only': cat_animals,
})

bokeh_fig.show_bokeh(
    row([
        column([row_slider, scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
    ])
)
