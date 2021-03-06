# -*- coding: utf-8 -*-

"""

<p>Perform a black or white top-hat transform on grayscale pixel data.</p>
<p>Top-hat transforms are useful for extracting small elements and details from images and volumes.</p>

"""

import skimage.morphology

import cellprofiler.module
import cellprofiler.setting


class TopHatTransform(cellprofiler.module.ImageProcessing):
    module_name = "TopHatTransform"

    variable_revision_number = 1

    def create_settings(self):
        super(TopHatTransform, self).create_settings()

        self.operation_name = cellprofiler.setting.Choice(
            choices=[
                "Black top-hat transform",
                "White top-hat transform"
            ],
            text="Operation",
            value="Black top-hat transform",
            doc="""
            Select the top-hat transformation:
            <ul>
                <li><i>Black top-hat transform</i>: This operation returns the dark spots of the image that are smaller
                than the structuring element. Note that dark spots in the original image are bright spots after the
                black top hat.</li>
                <li><i>White top-hat transform</i>: This operation returns the bright spots of the image that are
                smaller than the structuring element.</li>
            </ul>
            """
        )

        self.structuring_element = cellprofiler.setting.StructuringElement()

    def settings(self):
        __settings__ = super(TopHatTransform, self).settings()

        return __settings__ + [
            self.structuring_element
        ]

    def visible_settings(self):
        __settings__ = super(TopHatTransform, self).visible_settings()

        return __settings__ + [
            self.operation_name,
            self.structuring_element
        ]

    def run(self, workspace):
        if self.operation_name.value == "Black top-hat transform":
            self.function = skimage.morphology.black_tophat
        else:
            self.function = skimage.morphology.white_tophat

        super(TopHatTransform, self).run(workspace)
