# Using your own scatter point markers.
# E.g. when you want different sample types to use circles, squares, and triangles.

import pandas as pd

from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

data = pd.DataFrame({
    'x1': [1, 2, 3],
    'x2': [1, 4, 16],
    'x3': [1, 8, 64],
    'marker': ['circle', 'square', 'triangle'],
    'markerLegend': ['circle', 'square', 'triangle'],
})

bokeh_fig = BokehBioImageDataVis(
    data,
    output_filename='example_1c_custom_markers/vis.html',
)

scatter_plot = bokeh_fig.create_scatter_figure(markerKey='marker', markerLegendKey='markerLegend')

bokeh_fig.show_bokeh(scatter_plot)
