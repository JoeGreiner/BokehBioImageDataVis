import pandas as pd

# Step 0
# Define dataframe with numeric data (x1, x2, x3) and media data paths. The paths can be relative or absolute,
# but have to link to existing files. If they link to non-existing files, a 'missing data' image will be displayed.
# In a real-world scenario, you would load your experimental results, and construct matching paths for each
# datapoint. Media (plots, figures, images, 3D renders, ...) need to be generated previously.
data = pd.DataFrame({'x1': [1, 2, 3],
                     'x2': [1, 4, 16],
                     'x3': [1, 8, 64],
                     'path_to_images': ['data/pictures/cat1.jpg',
                                        'data/pictures/dog1.jpg',
                                        'data/pictures/dog2.jpg'],
                     'path_to_videos': ['data/videos/cat1.mp4',
                                        'data/videos/dog1.mp4',
                                        'data/videos/dog2.mp4']
                     })

# helper function that downloads example files
from BokehBioImageDataVis.src.utils import download_files_simple_example_1

download_files_simple_example_1()

# Step 1
# Create Main BokehBioImageDataVis figure and scatter plot object.
from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

bokeh_fig = BokehBioImageDataVis(data, output_filename='example_0_basic_use/vis.html')
scatter_plot = bokeh_fig.create_scatter_figure()

# Step 2
# Create image and video elements, and link them to the paths in the DataFrame by specifying their keys.
# Additionally, create a text element, that will display all available data for each datapoint in textform.
img_hover = bokeh_fig.add_image_hover(key='path_to_images')
vid_hover = bokeh_fig.add_video_hover(key='path_to_videos')
text_hover = bokeh_fig.create_hover_text()

# Step 3
# Compose the layout
from bokeh.layouts import column, row

bokeh_fig.show_bokeh(
    row([
        column([scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
    ])
)
