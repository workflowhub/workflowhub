from setuptools import setup

setup(
    name='wfchef.recipe.skeleton',
    version='0.1',
    packages=['skeleton'],
    include_package_data=True,
    install_requires=[
        'networkx',
        'workflowhub',
        'wfchef'
    ],
    entry_points = {
        'worfklow_recipes': [
            "skeleton = skeleton:SkeletonRecipe"
        ],
    }
)