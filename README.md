## BokehBioImageDataVis: <br>Explore and share scientific data through interactive, media-rich visualisations.
<p align="center">
  <img src="https://github.com/JoeGreiner/BokehBioImageDataVis/assets/24453528/9059ff3b-ee01-41b8-b174-d57255ae7b35" alt="bokeh">
  <br>
  <em>Interactive BokehBioImageDataVis website visualising results of a cardiomyocyte organelle analysis workflow.</em>
</p>

## What is BokehBioImageDataVis?

BokehBioImageDataVis is a simple but effective extension of the Bokeh visualisation library to link numerical data with diverse media types (e.g. metadata, images, videos) for interactive data exploration and sharing in collaborative scientific research. The core interaction mechanism of the framework is an interactive scatterplot, where users can select and display numerical features or dimensionality reduction embeddings of their dataset. Hovering over scatter points displays media data linked to each data point.

## 🏠 Table of Contents

* [Setup](#setup-)
* [Basic Use](#basic-use-)
* [Additional Features](#additional-features-)
* [Frequently Asked Questions (FAQ)](#faq-)

## Setup [🏠](#-table-of-contents)

1. Optional: Create a conda environment and activate it. 
```bash
conda create --name bokeh_vis python=3.9
conda activate bokeh_vis
```
2. Install BokehBioImageDataVis using pip.
```bash
pip install git+https://github.com/JoeGreiner/BokehBioImageDataVis.git
```

## Basic Use [🏠](#-table-of-contents)
### Code (see examples/0_basic_use.py)
1. Define dataframe with numeric data and media data paths. You can include an arbitrary amount of media (images, videos) with an arbitrary naming convention for the keys. The paths can be relative or absolute, but have to link to existing files. If they link to non-existing files, a 'missing data' image will be displayed. In a real-world scenario, you would load your experimental results, and construct matching paths for each datapoint. Media (plots, figures, images, 3D renders, ...) need to be generated previously.

The following code creates the structure, one row per datapoint, for the following datapoints:

|   | x1  | x2 | x3 | path_to_images         | path_to_videos        |
|---|----|----|----|------------------------|-----------------------|
| Sample 0 |  1 |  1 |  1 | data/pictures/cat1.jpg | data/videos/cat1.mp4  |
| Sample 1 |  2 |  4 |  8 | data/pictures/dog1.jpg | data/videos/dog1.mp4  |
| Sample 2 |  3 | 16 | 64 | data/pictures/dog2.jpg | data/videos/dog2.mp4  |

x1, x2, x3 represent numerical features that could be used to explore the data, e.g. the volume, weight, area (...) of each sample.
 
```python
import pandas as pd
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
```

2. Create Main BokehBioImageDataVis figure and scatter plot object.
```python
from BokehBioImageDataVis.BokehBioImageDataVis import BokehBioImageDataVis

bokeh_fig = BokehBioImageDataVis(data, output_filename='example_0_basic_use/vis.html')
scatter_plot = bokeh_fig.create_scatter_figure()
```

3. Create image and video elements, and link them to the paths in the DataFrame by specifying their keys. Additionally, create a text element, that will display all available data for each datapoint in textform.
```python
img_hover = bokeh_fig.add_image_hover(key='path_to_images')
vid_hover = bokeh_fig.add_video_hover(key='path_to_videos')
text_hover = bokeh_fig.create_hover_text()
```

4. Compose the final layout.
```python
from bokeh.layouts import column, row

bokeh_fig.show_bokeh(
    row([
        column([scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
    ])
)
```
### Expected Results
Running the code should open the website shown below. If the website does not automatically open, navigate to the output directory (here: 'example_0_basic_use'), and open the website (here: 'vis.html'). The resulted website is portable, i.e., you can share them with others by sending around the output folder (you probably want to create an archive/zip to do so).

<p align="center">
  <img src="https://github.com/JoeGreiner/BokehBioImageDataVis/assets/24453528/93612315-b19b-4ac2-b58c-74172231bc05" alt="bokeh">
  <br>
  <em>Expected outcome of the basic usage example.</em>
</p>

## Additional Features [🏠](#-table-of-contents)
* [examples/1a_categories.py](examples/1a_categories.py)
  Color scatter points by category.

* [examples/1b_custom_colors.py](examples/1b_custom_colors.py)
  Scatter point colors.

* [examples/1c_custom_markers.py](examples/1c_custom_markers.py)
  Scatter point markers.

* [examples/1d_combined_styling.py](examples/1d_combined_styling.py)
  Combine categories, custom colors, custom markers, and legend placement.

* [examples/2_media_panels.py](examples/2_media_panels.py)
  Image and video sizing, media titles, duplicate media panels, and filtered hover text.

* [examples/3_controls.py](examples/3_controls.py)
  Default axes, the row slider, the legend help button, and the global video toggle.

* [examples/4_named_datasets.py](examples/4_named_datasets.py)
  Switching between named datasets while keeping the same layout and linked widgets.

## FAQ [🏠](#-table-of-contents)

* How do I generate media (automatically)?

This depends really on what you want to visualise. Matplotlib (2D figures) and ParaView (3D renders) are great choices for many applications. Please do not hesitate to contact me if you're stuck here.

* I get 'missing data' symbols on my website. Why?

The paths that you have specified do not exist, and therefore can't be linked. Make sure that the paths are correct. It does not matter if you use relative or absolute paths, the framework will copy all media to the output directory next to the website and link them relatively, so that the output folder can be moved to other computers with the links still working.

* How do I share a website?

Just share the output folder – the website will work seamlessly in different locations. Alternatively, you can host the website online.

* I've shared the website with a collaborator, however, he doesn't see any media elements. Why?

I've realised that occasionally, when I send collaborators a visualisation as an archive, they don't unzip/extract the archive, but try to run the website from within the archive. Doing so will not show any media elements, as the paths are incorrect. If you send an archive/zip, people need to extract/unarchive the folder first before visiting the website. I now generate a textfile stating 'PLEASE_MAKE_SURE_IM_UNZIPPED.txt', I hope that helps to circumvent these issues :-)

## Shoutouts

In addition to BokehBioImageDataVis, there are other absolutely fantastic tools available for similar or related visualisation tasks that might be of interest. You may want to check them out too, as they have a different focus and ecosystem. Please note that I developed BokehBioImageDataVis independently and have no affiliation with these other tools.

* [IDE (Image Data Explorer)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0273698) <br>Especially cool if you work within the R ecosystem and you are looking to integrate data analysis with the visualisation workflow.

* [MoBIE (MultiModal Big Image Data Sharing and Exploration)](https://www.nature.com/articles/s41592-023-01776-4)<br>Especially cool if you work within the Fiji/BDV ecosystem and have massive image data (TB, cloud-stored) to explore and visualise.
