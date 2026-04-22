# Using your own scatter point colors.
# E.g. when you already have fixed colors that should be used in the plot.

import pandas as pd

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

data = pd.DataFrame({
    'x1': [1, 2, 3],
    'x2': [1, 4, 16],
    'x3': [1, 8, 64],
    'colors': ['#e28743', '#0f0f0f', '#00ff00'],
    'colorLegend': ['orange sample', 'black sample', 'green sample'],
})

bokeh_fig = BokehBioImageDataVis(
    data,
    output_filename='example_1b_custom_colors/vis.html',
)

scatter_plot = bokeh_fig.create_scatter_figure(
    colorKey='colors',
    colorLegendKey='colorLegend',
)

bokeh_fig.show_bokeh(scatter_plot)
