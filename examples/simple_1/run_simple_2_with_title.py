import pandas as pd
from bokeh.layouts import column, row

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

data = pd.DataFrame({'x1': [1, 2, 3],
                     'x2': [1, 4, 16],
                     'x3': [1, 8, 64],
                     'animal': ['cat', 'dog', 'dog'],
                     'path_to_images': ['data/pictures/cat1.jpg',
                                        'data/pictures/dog1.jpg',
                                        'data/pictures/dog2.jpg'],
                     'path_to_videos': ['data/videos/cat1.mp4',
                                        'data/videos/dog1.mp4',
                                        'data/videos/dog2.mp4']
                     })

# create main object
bokeh_fig = BokehBioImageDataVis(data, output_filename='example_simple_2/vis.html', category_key='animal')
scatter_plot = bokeh_fig.create_scatter_figure()

# create hovers
img_hover = bokeh_fig.add_image_hover(key='path_to_images', title='cat picture')
vid_hover = bokeh_fig.add_video_hover(key='path_to_videos', title='cat video')

text_hover = bokeh_fig.create_hover_text()

id_slider = bokeh_fig.add_slider()


# compose figure
bokeh_fig.show_bokeh(
    row([
        column([id_slider, scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
    ])
)

