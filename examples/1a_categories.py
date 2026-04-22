# Coloring scatter points by category.
# E.g. when you want sample groups such as cats and dogs to be easy to distinguish.

import pandas as pd

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

data = pd.DataFrame({
    'x1': [1, 2, 3],
    'x2': [1, 4, 16],
    'x3': [1, 8, 64],
    'animal': ['cat', 'dog', 'dog'],
})

bokeh_fig = BokehBioImageDataVis(
    data,
    output_filename='example_1a_categories/vis.html',
    category_key='animal',
)

scatter_plot = bokeh_fig.create_scatter_figure()

bokeh_fig.show_bokeh(scatter_plot)
