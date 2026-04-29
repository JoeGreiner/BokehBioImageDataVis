from setuptools import setup, find_packages

setup(name='BokehBioImageDataVis',
      version='0.2',
      description='Helper functions to display/explore bioimage data',
      url='tbd',
      author='Joachim Greiner',
      author_email='joe@joegreiner.de',
      license='MIT',
      packages=find_packages(),
      python_requires='>=3.8',
      install_requires=[
          'bokeh>=2.4,<3; python_version < "3.10"',
          'bokeh>=3.9,<4; python_version >= "3.10"',
          'pandas>=2.0,<4',
          'numpy>=1.24,<2; python_version < "3.10"',
          'numpy>=2.2,<3; python_version >= "3.10"',
          'requests',
          'ffmpeg-python',
      ],
      package_data={
        'BokehBioImageDataVis': ['resources/*.png', 'resources/*.mp4']
        },
      zip_safe=False)
