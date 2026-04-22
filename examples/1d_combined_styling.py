# Combining categories, custom colors, and custom markers in one scatter plot.
# E.g. when you want full control over how different sample groups are shown.

import pandas as pd

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

data = pd.DataFrame({
    'x1': [1, 2, 3],
    'x2': [1, 4, 16],
    'x3': [1, 8, 64],
    'animal': ['cat', 'dog', 'dog'],
    'colors': ['#e28743', '#0f0f0f', '#00ff00'],
    'colorLegend': ['simba', 'bello', 'rex'],
    'marker': ['circle', 'square', 'triangle'],
    'markerLegend': ['(neutral)', '(good)', '(very good)'],
})

bokeh_fig = BokehBioImageDataVis(
    data,
    output_filename='example_1d_combined_styling/vis.html',
    category_key='animal',
    legend_position='outside',
    legend_title='Style Legend',
    x_axis_key='x3',
    y_axis_key='x2',
)

scatter_plot = bokeh_fig.create_scatter_figure(
    markerKey='marker',
    markerLegendKey='markerLegend',
    colorKey='colors',
    colorLegendKey='colorLegend',
)

bokeh_fig.show_bokeh(scatter_plot)
