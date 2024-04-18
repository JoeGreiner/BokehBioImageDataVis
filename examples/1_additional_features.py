import pandas as pd

# Step 0
# Define dataframe with numeric data (x1, x2, x3) and media data paths. The paths can be relative or absolute,
# but have to link to existing files. If they link to non-existing files, a 'missing data' image will be displayed.
# In a real-world scenario, you would load your experimental results, and construct matching paths for each
# datapoint. Media (plots, figures, images, 3D renders, ...) need to be generated previously.
data = pd.DataFrame({'x1': [1, 2, 3],
                     'x2': [1, 4, 16],
                     'x3': [1, 8, 64],
                     'animal': ['cat', 'dog', 'dog'], # new column for category key feature (see later)
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

# FEATURE: Category Key
# add a category key to the BokehBioImageDataVis object, to color the scatter plot by the categories in the DataFrame
# position of the legend can be set with the legend_position argument
# FEATURE: Default Axis Keys
# set default axis keys for the scatter plot, can be changed interactively
bokeh_fig = BokehBioImageDataVis(data, output_filename='example_1_additional_features/vis.html', category_key='animal',
                                 legend_position='top_left', x_axis_key='x3', y_axis_key='x2')
scatter_plot = bokeh_fig.create_scatter_figure()

# Step 2
# Create image and video elements, and link them to the paths in the DataFrame by specifying their keys.
# Additionally, create a text element, that will display all available data for each datapoint in textform.

# FEATURE: Scaling
# add width and height to scale the images and videos by providing hover with width and height arguments
# FEATURE: Titles
# add titles to the images and videos
# FEATURE: Legend Text
# add legend text to the images and videos, can be formatted with html tags, needs legend_button to be added to the plot
# see later in the code

obj_width = 550
obj_height = 400
img_hover = bokeh_fig.add_image_hover(key='path_to_images',
                                      width=obj_width, height=obj_height,
                                      title='animal picture',
                                      legend_text='<span style="color:red">animal picture</span>'
                                                  'Cats \n <i>Dogs</i> \n and so on!')

# FEATURE: Video Autoplay
# control if videos should automatically start playing
vid_hover = bokeh_fig.add_video_hover(key='path_to_videos',
                                      width=obj_width, height=obj_height,
                                      title='animal video', autoplay=True,
                                      legend_text='<span style="color:green">animal video</span>'
                                                  'Cats \n <i>Dogs</i> \n and so on!')

legend_str_dup = '<p>A <span style="text-decoration: underline; color:cyan">video</span> of a cute animal.</p>'

duplicate_vid_hover = bokeh_fig.add_video_hover(key='path_to_videos',
                                                width=obj_width, height=obj_height,
                                                title='animal video', autoplay=True,
                                                legend_text=legend_str_dup)

# FEATURE: ignore_keys
# ignore keys in the text_hover, can be a list of keys -- you may want to not show auxiliary data in the text_hover
text_hover = bokeh_fig.create_hover_text(ignore_keys=['color_mapping', 'x2'])

# FEATURE: Slider
# add a slider to the plot, when clicked on, can be controlled with arrow keys to quickly navigate through the data
id_slider = bokeh_fig.add_slider()

# FEATURE: Legend Button
# Show or hide the legend, legends have to be defined in the image and video hovers
legend_button = bokeh_fig.add_legend()  # has to be called after adding all other image and video elements!

# FEATURE: Video Toggle Button
# Toggle the video playback on and off for all videos shown simultaneously
video_toggle_button = bokeh_fig.add_toggle_video_button()

# Step 3
# Compose the layout
from bokeh.layouts import column, row

bokeh_fig.show_bokeh(
    row([
        column([row([legend_button, video_toggle_button]), id_slider, scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
        duplicate_vid_hover
    ])
)
