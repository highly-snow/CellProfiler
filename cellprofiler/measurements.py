"""Measurements.py - storage for image and object measurements

CellProfiler is distributed under the GNU General Public License.
See the accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2012 Broad Institute
All rights reserved.

Please see the AUTHORS file for credits.

Website: http://www.cellprofiler.org
"""
from __future__ import with_statement

__version__ = "$Revision$"

import json
import logging
logger = logging.getLogger(__name__)
import numpy as np
import re
from scipy.io.matlab import loadmat
from itertools import repeat
import cellprofiler.preferences as cpprefs
from cellprofiler.utilities.hdf5_dict import HDF5Dict, get_top_level_group
from cellprofiler.utilities.hdf5_dict import VERSION
import tempfile
import numpy as np
import warnings
import os
import os.path
import mmap

AGG_MEAN = "Mean"
AGG_STD_DEV = "StDev"
AGG_MEDIAN = "Median"
AGG_NAMES = [AGG_MEAN, AGG_MEDIAN, AGG_STD_DEV]

"""The per-image measurement category"""
IMAGE = "Image"

"""The per-experiment measurement category"""
EXPERIMENT = "Experiment"

"""The relationship measurement category"""
RELATIONSHIP = "Relationship"

"""The neighbor association measurement category"""
NEIGHBORS = "Neighbors"

"""The per-object "category" (if anyone needs the word, "Object")"""
OBJECT = "Object"

disallowed_object_names = [IMAGE, EXPERIMENT, RELATIONSHIP]

COLTYPE_INTEGER = "integer"
COLTYPE_FLOAT = "float"
'''16bit Binary Large Object. This object can fit 64K of raw data.
Currently used for storing image thumbnails as 200 x 200px (max) 8-bit pngs.
Should NOT be used for storing larger than 256 x 256px 8-bit pngs.'''
COLTYPE_BLOB = "blob"
'''24bit Binary Large Object. This object can fit 16M of raw data.
Not currently used'''
COLTYPE_MEDIUMBLOB = "mediumblob"
'''32bit Binary Large Object. This object can fit 4GB of raw data.
Not currently used'''
COLTYPE_LONGBLOB = "longblob"
'''SQL format for a varchar column

To get a varchar column of width X: COLTYPE_VARCHAR_FORMAT % X
'''
COLTYPE_VARCHAR_FORMAT = "varchar(%d)"
COLTYPE_VARCHAR = "varchar"
'''# of characters reserved for path name in the database'''
PATH_NAME_LENGTH = 256
'''# of characters reserved for file name in the database'''
FILE_NAME_LENGTH = 128
COLTYPE_VARCHAR_FILE_NAME = COLTYPE_VARCHAR_FORMAT % FILE_NAME_LENGTH
COLTYPE_VARCHAR_PATH_NAME = COLTYPE_VARCHAR_FORMAT % PATH_NAME_LENGTH

'''Column attribute: only available after post_group is run (True / False)'''
MCA_AVAILABLE_POST_GROUP  = "AvailablePostGroup"

'''The name of the metadata category'''
C_METADATA = "Metadata"

'''The name of the site metadata feature'''
FTR_SITE = "Site"

'''The name of the well metadata feature'''
FTR_WELL = "Well"

'''The name of the row metadata feature'''
FTR_ROW = "Row"

'''The name of the column metadata feature'''
FTR_COLUMN = "Column"

'''The name of the plate metadata feature'''
FTR_PLATE = "Plate"

M_SITE, M_WELL, M_ROW, M_COLUMN, M_PLATE = \
      ['_'.join((C_METADATA, x))
       for x in (FTR_SITE, FTR_WELL, FTR_ROW, FTR_COLUMN, FTR_PLATE)]

MEASUREMENTS_GROUP_NAME = "Measurements"
IMAGE_NUMBER = "ImageNumber"
OBJECT_NUMBER = "ObjectNumber"
GROUP_NUMBER = "Group_Number"  # 1-based group index
GROUP_INDEX = "Group_Index"  # 1-based index within group

'''The FileName measurement category'''
C_FILE_NAME = "FileName"

'''The PathName measurement category'''
C_PATH_NAME = "PathName"

'''The URL measurement category'''
C_URL = "URL"

'''The series of an image file'''
C_SERIES = "Series"

'''The frame of a movie file'''
C_FRAME = "Frame"

'''The channel # of a color image plane'''
C_CHANNEL = "Channel"

'''The FileName measurement category when loading objects'''
C_OBJECTS_FILE_NAME = "ObjectsFileName"

'''The PathName measurement category when loading objects'''
C_OBJECTS_PATH_NAME = "ObjectsPathName"

'''The URL category when loading objects'''
C_OBJECTS_URL = "ObjectsURL"

'''The series of an image file'''
C_OBJECTS_SERIES = "ObjectsSeries"

'''The index of an image file'''
C_OBJECTS_FRAME = "ObjectsFrame"

'''The channel # of a color image plane'''
C_OBJECTS_CHANNEL = "ObjectsChannel"

'''The ChannelType experiment measurement category'''
C_CHANNEL_TYPE = "ChannelType"

'''The experiment feature name used to store the image set's metadata tags'''
M_METADATA_TAGS = "_".join((C_METADATA, "Tags"))

def get_length_from_varchar(x):
    '''Retrieve the length of a varchar column from its coltype def'''
    m = re.match(r'^varchar\(([0-9]+)\)$', x)
    if m is None:
        return None
    return int(m.groups()[0])

class Measurements(object):
    """Represents measurements made on images and objects
    """
    def __init__(self,
                 can_overwrite=False,
                 image_set_start=None,
                 filename = None,
                 copy = None,
                 mode = "w"):
        """Create a new measurements collection

        can_overwrite - DEPRECATED and has no effect
        image_set_start - the index of the first image set in the image set list
                          or None to start at the beginning
        filename - store the measurement in an HDF5 file with this name
        copy - initialize by copying measurements from here, either an HDF5Dict
               or an H5py group or file.
        mode - open mode for the HDF5 file. 
               "r" for read-only access to an existing measurements file, 
               "w" to open a new file or truncate an old file, 
               "w-" to open a new file and fail if the file exists,
               "w+" to create a new measurements instance in an existing file,
               "a" to create a new file or open an existing file as read/write
               "r+" to open an existing file as read/write
               "memory" to create an HDF5 memory-backed File
        """
        # XXX - allow saving of partial results
        if mode is "memory":
            filename = None
            mode = "w"
            is_temporary = False
        elif filename is None:
            dir = cpprefs.get_default_output_directory()
            if not (os.path.exists(dir) and os.access(dir, os.W_OK)):
                dir = None
            fd, filename = tempfile.mkstemp(prefix='Cpmeasurements', suffix='.hdf5', dir=dir)
            is_temporary = True
        else:
            is_temporary = False
        if isinstance(copy, Measurements):
            with copy.hdf5_dict.lock:
                self.hdf5_dict = HDF5Dict(
                    filename, 
                    is_temporary = is_temporary,
                    copy = copy.hdf5_dict.top_group,
                    mode = mode)
        elif hasattr(copy, '__getitem__') and hasattr(copy, 'keys'):
            self.hdf5_dict = HDF5Dict(
                filename,
                is_temporary = is_temporary,
                copy = copy,
                mode = mode)
        elif copy is not None:
            raise ValueError('Copy source for measurments is neither a Measurements or HDF5 group.')
        else:
            self.hdf5_dict = HDF5Dict(filename, 
                                      is_temporary = is_temporary,
                                      mode = mode)
        if is_temporary:
            os.close(fd)

        self.image_set_number = image_set_start or 1
        self.image_set_start = image_set_start

        self.__is_first_image = True
        self.__initialized_explicitly = False
        self.__relationships = set()
        self.__relationship_names = set()
        self.__images = {}
        self.__image_providers = []
        self.__images = {}
        self.__image_providers = []

    def __del__(self):
        if hasattr(self, "hdf5_dict"):
            self.close()

    def close(self):
        self.hdf5_dict.close()
        del self.hdf5_dict
        
    def __getitem__(self, key):
        # we support slicing the last dimension for the limited case of [..., :]
        if len(key) == 3 and key[2] == slice(None, None, None):
            return self.get_all_measurements(*key[:2])
        return self.get_measurement(*key)

    def __setitem__(self, key, value):
        assert 2 <= len(key) <= 3
        if len(key) == 2:
            self.add_measurement(key[0], key[1], value)
        else:
            self.add_measurement(key[0], key[1], value, image_set_number=key[2])

    def flush(self):
        self.hdf5_dict.flush()

    def file_contents(self):
        return self.hdf5_dict.file_contents()

    def initialize(self, measurement_columns):
        '''Initialize the measurements with a list of objects and features

        This explicitly initializes the measurements with a list of
        object/feature pairs as would be returned by
        get_measurement_columns()

        measurement_columns - list of 3-tuples: object name, feature, type
        '''
        # clear the old data, if any
        self.hdf5_dict.clear()

        def fix_type(t):
            if t == 'integer':
                return np.int
            if t.startswith('varchar'):
                len = t.split('(')[1][:-1]
                return np.dtype('a' + len)
            return t

        for object_name, feature, coltype in measurement_columns:
            coltype = fix_type(coltype)
            if object_name == EXPERIMENT:
                dims = 0
            elif object_name == IMAGE:
                dims = 1
            else:
                dims = 2
            self.hdf5_dict.add_object(object_name)
            self.hdf5_dict.add_feature(object_name, feature)
        self.__initialized_explicitly = True

    def next_image_set(self, explicit_image_set_number=None):
        assert explicit_image_set_number is None or explicit_image_set_number > 0
        if explicit_image_set_number is None:
            self.image_set_number += 1
        else:
            self.image_set_number = explicit_image_set_number
        self.__is_first_image = False
        self.__images = {}
        self.__image_providers = []

    @property
    def image_set_count(self):
        '''The number of complete image sets measured'''
        # XXX - question for Lee: should this return the minimum number
        # of non-null values across columns in the the Image table?
        try:
            return len(self.hdf5_dict.get_indices('Image', 'ImageNumber'))
        except KeyError:
            return 0

    def get_is_first_image(self):
        '''True if this is the first image in the set'''
        return self.__is_first_image

    def set_is_first_image(self, value):
        if not value:
            raise ValueError("Can only reset to be first image")
        self.__is_first_image = True
        self.image_set_number = self.image_set_start_number

    is_first_image = property(get_is_first_image, set_is_first_image)

    @property
    def image_set_start_number(self):
        '''The first image set (one-based) processed by the pipeline'''
        if self.image_set_start is None:
            return 1
        return self.image_set_start

    @property
    def has_image_set_start(self):
        '''True if the image set has an explicit start'''
        return self.image_set_start is not None

    def load(self, measurements_file_name):
        '''Load measurements from a matlab file'''
        handles = loadmat(measurements_file_name, struct_as_record=True)
        self.create_from_handles(handles)

    def create_from_handles(self, handles):
        '''Load measurements from a handles structure'''
        m = handles["handles"][0, 0][MEASUREMENTS_GROUP_NAME][0, 0]
        for object_name in m.dtype.fields.keys():
            omeas = m[object_name][0, 0]
            for feature_name in omeas.dtype.fields.keys():
                if object_name == IMAGE:
                    values = [None if len(x) == 0 else x.flatten()[0] 
                              for x in omeas[feature_name][0]]
                elif object_name == EXPERIMENT:
                    value = omeas[feature_name][0, 0].flatten()[0]
                    self.add_experiment_measurement(feature_name, value)
                    continue
                else:
                    values = [x.flatten()
                              for x in omeas[feature_name][0].tolist()]
                self.add_all_measurements(object_name,
                                          feature_name,
                                          values)
        #
        # Set the image set number to beyond the last in the handles
        #
        self.image_set_number = self.image_set_count + 1

    def add_image_measurement(self, feature_name, data, can_overwrite = False):
        """Add a measurement to the "Image" category

        """
        self.add_measurement(IMAGE, feature_name, data)

    def add_experiment_measurement(self, feature_name, data):
        """Add an experiment measurement to the measurement

        Experiment measurements have one value per experiment
        """
        if isinstance(data, basestring):
            data = unicode(data).encode('unicode_escape')
        self.hdf5_dict.add_all(EXPERIMENT, feature_name, [data], [0])

    def get_group_number(self):
        '''The number of the group currently being processed'''
        return self.get_current_image_measurement(GROUP_NUMBER)

    def set_group_number(self, group_number, can_overwrite=False):
        self.add_image_measurement(GROUP_NUMBER, group_number)

    group_number = property(get_group_number, set_group_number)

    def get_group_index(self):
        '''The within-group index of the current image set'''
        return self.get_current_image_measurement(GROUP_INDEX)

    def set_group_index(self, group_index):
        self.add_image_measurement(GROUP_INDEX, group_index)

    group_index = property(get_group_index, set_group_index)
    
    def get_groupings(self, features):
        '''Return groupings of image sets based on feature values
        
        features - a sequence of feature names
                   
        returns groupings suitable for return from CPModule.get_groupings.
        
        group_list - a sequence composed of two-tuples.
                     the first element of the tuple is a dictionary giving
                     the metadata values for the metadata keys
                     the second element of the tuple is a sequence of
                     image numbers comprising the image sets of the group
        For instance, an experiment might have key_names of 'Metadata_Row'
        and 'Metadata_Column' and a group_list of:
        [ ({'Metadata_Row':'A','Metadata_Column':'01'}, [1,97,193]),
          ({'Metadata_Row':'A','Metadata_Column':'02'), [2,98,194]),... ]
        '''
        d = {}
        image_numbers = self.get_image_numbers()
        values = [[unicode(x) for x in self.get_measurement(IMAGE, feature, image_numbers)]
                  for feature in features]
        for i, image_number in enumerate(image_numbers):
            key = tuple([(k, v[i]) for k, v in zip(features, values)])
            if not d.has_key(key):
                d[key] = []
            d[key].append(image_number)
        return [ (dict(k), d[k]) for k in sorted(d.keys()) ]
            

    def add_relate_measurement(
        self, module_number,
        relationship,
        object_name1, object_name2,
        group_indexes1, object_numbers1,
        group_indexes2, object_numbers2):
        '''Add object relationships to the measurements

        module_number - the module that generated the relationship

        relationship - the relationship of the two objects, for instance,
                       "Parent" means object # 1 is the parent of object # 2

        object_name1, object_name2 - the name of the segmentation for the first and second objects

        group_indexes1, group_indexes2 - for each object, the group index of
                                         that object's image set.
                                         (MUST NOT BE A SCALAR)

        object_numbers1, object_numbers2 - for each object, the object number
                                           in the object's object set

        This method lets the caller store any sort of arbitrary relationship
        between objects as long as they are in the same group. To record
        all neighbors within a particular segmentation, call with the same
        object name for object_name1 and object_name2 and the same group
        index - that of the current image. Relating would have different object
        names and TrackObjects would have different group indices.
        '''

        # XXX - check overwrite?
        # XXX - Should group number be moved out of the measurement name?
        group_number = self.group_number
        with self.hdf5_dict.lock:
            self.hdf5_dict.top_group.require_group(RELATIONSHIP)
            relationship_group = self.hdf5_dict.top_group.require_group('%s/%02d_%d_%s_%s_%s' % (RELATIONSHIP, module_number, group_number, relationship, object_name1, object_name2))
            features = ["group_number", "group_index1", "group_index2", "object_number1", "object_number2"]
            if "group_number" not in relationship_group:
                for name in features:
                    relationship_group.create_dataset(name, (0,), dtype='int32', chunks=(1024,), maxshape=(None,))
            current_size = relationship_group['group_number'].shape[0]
            for name in features:
                relationship_group[name].resize((current_size + len(group_indexes1),))
            relationship_group['group_number'][current_size:] = group_number
            relationship_group['group_index1'][current_size:] = group_indexes1
            relationship_group['group_index2'][current_size:] = group_indexes2
            relationship_group['object_number1'][current_size:] = object_numbers1
            relationship_group['object_number2'][current_size:] = object_numbers2
            self.__relationships.add((module_number, group_number, relationship, object_name1, object_name2))
            self.__relationship_names.add(relationship_group.name)

    def get_relationship_groups(self):
        '''Return the keys of each of the relationship groupings.

        The value returned is a list composed of objects with the following
        attributes:
        module_number - the module number of the module used to generate the relationship
        group_number - the group number of the relationship
        relationship - the relationship of the two objects
        object_name1 - the object name of the first object in the relationship
        object_name2 - the object name of the second object in the relationship
        '''

        return [RelationshipKey(module_number, group_number, relationship, obj1, obj2) for
                (module_number, group_number, relationship, obj1, obj2) in self.__relationships]

    def get_relationships(self, module_number, relationship, object_name1, object_name2, group_number):
        if not (module_number, group_number, relationship, object_name1, object_name2) in self.__relationships:
            return np.zeros(0, [("group_index1", int, 1),
                                ("object_number1", int, 1),
                                ("group_index2", int, 1),
                                ("object_number2", int, 1)]).view(np.recarray)
        with self.hdf5_dict.lock:
            grp = self.hdf5_dict.top_group['%s/%02d_%d_%s_%s_%s' % (RELATIONSHIP, module_number, group_number, relationship, object_name1, object_name2)]
            dt = np.dtype([("group_index1", np.int, 1),
                           ("object_number1", np.int, 1),
                           ("group_index2", np.int, 1),
                           ("object_number2", np.int, 1)])
            temp = np.zeros(grp['group_index1'].shape, dt)
            temp['group_index1'] = grp['group_index1']
            temp['object_number1'] = grp['object_number1']
            temp['group_index2'] = grp['group_index2']
            temp['object_number2'] = grp['object_number2']
            return temp.view(np.recarray)

    def add_measurement(self, object_name, feature_name, data, 
                        can_overwrite=False, image_set_number=None):
        """Add a measurement or, for objects, an array of measurements to the set

        This is the classic interface - like CPaddmeasurements:
        ObjectName - either the name of the labeled objects or "Image"
        FeatureName - the feature name, encoded with underbars for category/measurement/image/scale
        Data - the data item to be stored
        """
        if image_set_number is None:
            image_set_number = self.image_set_number

        # some code adds ImageNumber and ObjectNumber measurements explicitly
        if feature_name in (IMAGE_NUMBER, OBJECT_NUMBER):
            return

        def wrap_string(v):
            if isinstance(v, basestring):
                return unicode(v).encode('unicode_escape')
            return v

        if object_name == EXPERIMENT:
            if not np.isscalar(data) and data is not None:
                data = data[0]
            if data is None:
                data = []
            self.hdf5_dict[EXPERIMENT, feature_name, 0] = wrap_string(data)
        elif object_name == IMAGE:
            if not np.isscalar(data) and data is not None:
                data = data[0]
            if data is None:
                data = []
            self.hdf5_dict[IMAGE, feature_name, image_set_number] = wrap_string(data)
            if not self.hdf5_dict.has_data(object_name, 'ImageNumber', image_set_number):
                self.hdf5_dict[IMAGE, 'ImageNumber', image_set_number] = image_set_number
        else:
            self.hdf5_dict[object_name, feature_name, image_set_number] = data
            if not self.hdf5_dict.has_data(IMAGE, IMAGE_NUMBER, image_set_number):
                self.hdf5_dict[IMAGE, IMAGE_NUMBER, image_set_number] = image_set_number
            if not self.hdf5_dict.has_data(object_name, 'ObjectNumber', image_set_number):
                self.hdf5_dict[object_name, 'ImageNumber', image_set_number] = [image_set_number] * len(data)
                self.hdf5_dict[object_name, 'ObjectNumber', image_set_number] = np.arange(1, len(data) + 1)
                
    def remove_measurement(self, object_name, feature_name, image_number):
        '''Remove the measurement for the given image number
        
        object_name - the measurement's object. If other than Image or Experiment,
                      will remove measurements for all objects
        feature_name - name of the measurement feature
        image_number - the image set's image number
        '''
        del self.hdf5_dict[object_name, feature_name, image_number]
        
    def clear(self):
        '''Remove all measurements'''
        self.hdf5_dict.clear()

    def get_object_names(self):
        """The list of object names (including Image) that have measurements
        """
        return [x for x in self.hdf5_dict.top_level_names()
                if x != RELATIONSHIP]

    object_names = property(get_object_names)

    def get_feature_names(self, object_name):
        """The list of feature names (measurements) for an object
        """
        return [name for name in self.hdf5_dict.second_level_names(object_name) if name not in ('ImageNumber', 'ObjectNumber')]
    
    def get_image_numbers(self):
        '''Return the image numbers from the Image table'''
        image_numbers = np.array(
            self.hdf5_dict.get_indices(IMAGE, IMAGE_NUMBER), int)
        image_numbers.sort()
        return image_numbers
    
    def reorder_image_measurements(self, new_image_numbers):
        '''Assign all image measurements to new image numbers
        
        new_image_numbers - a zero-based array that maps old image number
                            to new image number, e.g. if 
                            new_image_numbers = [ 0, 3, 1, 2], then
                            the measurements for old image number 1 will
                            be the measurements for new image number 3, etc.
                            
        Note that this does not handle any image numbers that might be stored
        in the measurements themselves. It is intended for use in
        prepare_run when it is necessary to reorder image numbers because
        of regrouping.
        '''
        for feature in self.get_feature_names(IMAGE):
            self.hdf5_dict.reorder(IMAGE, feature, new_image_numbers)

    def has_feature(self, object_name, feature_name):
        return self.hdf5_dict.has_feature(object_name, feature_name)

    def get_current_image_measurement(self, feature_name):
        '''Return the value for the named image measurement

        feature_name - the name of the measurement feature to be returned
        '''
        return self.get_current_measurement(IMAGE, feature_name)

    def get_current_measurement(self, object_name, feature_name):
        """Return the value for the named measurement for the current image set
        object_name  - the name of the objects being measured or "Image"
        feature_name - the name of the measurement feature to be returned
        """
        return self.get_measurement(object_name, feature_name, self.image_set_number)

    def get_measurement(self, object_name, feature_name, image_set_number=None):
        """Return the value for the named measurement and indicated image set
        
        object_name - the name of one of the objects or one of the generic
                      names such as Image or Experiment
                      
        feature_name - the name of the feature to retrieve 
        
        image_set_number - the current image set by default, a single 
                           image set number to get measurements for one
                           image set or a sequence of image numbers to
                           return measurements for each of the image sets
                           listed.
        """
        def unwrap_string(v):
            # hdf5 returns string columns as a wrapped type
            if isinstance(v, str):
                return unicode(str(v)).decode('unicode_escape')
            return v
        if object_name == EXPERIMENT:
            return unwrap_string(self.hdf5_dict[EXPERIMENT, feature_name, 0][0])
        if image_set_number is None:
            image_set_number = self.image_set_number
        vals = self.hdf5_dict[object_name, feature_name, image_set_number]
        if vals is None:
            return None
        if object_name == IMAGE:
            if np.isscalar(image_set_number):
                return np.NAN if len(vals) == 0 else unwrap_string(vals[0])
            else:
                return np.array(
                    [unwrap_string(v[0]) if v is not None else np.NaN
                     for v in vals])
        if np.isscalar(image_set_number):
            return np.array([]) if vals is None else vals.flatten()
        return [np.array([]) if v is None else v.flatten() for v in vals]

    def has_measurements(self, object_name, feature_name, image_set_number):
        if object_name == EXPERIMENT:
            return self.hdf5_dict.has_data(EXPERIMENT, feature_name, 0)
        return self.hdf5_dict.has_data(object_name, feature_name, image_set_number)

    def has_current_measurements(self, object_name, feature_name):
        return self.has_measurements(object_name, feature_name, self.image_set_number)

    def get_all_measurements(self, object_name, feature_name):
        warnings.warn("get_all_measurements is deprecated. Please use "
                      "get_measurements with an array of image numbers instead",
                      DeprecationWarning)
        return self.get_measurement(object_name, feature_name,
                                    self.get_image_numbers())

    def add_all_measurements(self, object_name, feature_name, values):
        '''Add a list of measurements for all image sets

        object_name - name of object or Images
        feature_name - feature to add
        values - list of either values or arrays of values
        '''
        values = [unicode(value).encode('unicode_escape') 
                  if isinstance(value, (str, unicode)) else value
                  for value in values]
        if ((not self.hdf5_dict.has_feature(IMAGE, IMAGE_NUMBER)) or
            (np.max(self.get_image_numbers()) < len(values))):
            self.hdf5_dict.add_all(
                IMAGE, IMAGE_NUMBER, 
                [i+1 if value is not None else None 
                 for i, value in enumerate(values)])
        self.hdf5_dict.add_all(object_name, feature_name, values)

    def get_experiment_measurement(self, feature_name):
        """Retrieve an experiment-wide measurement
        """
        return self.get_measurement(EXPERIMENT, feature_name) or 'N/A'

    def apply_metadata(self, pattern, image_set_number=None):
        """Apply metadata from the current measurements to a pattern

        pattern - a regexp-like pattern that specifies how to insert
                  metadata into a string. Each token has the form:
                  "\(?<METADATA_TAG>\)" (matlab-style) or
                  "\g<METADATA_TAG>" (Python-style)
        image_name - name of image associated with the metadata (or None
                     if metadata is not associated with an image)
        image_set_number - # of image set to use to retrieve data.
                           None for current.
        returns a string with the metadata tags replaced by the metadata
        """
        if image_set_number == None:
            image_set_number = self.image_set_number
        result_pieces = []
        double_backquote = "\\\\"
        single_backquote = "\\"
        for piece in pattern.split(double_backquote):
            # Replace tags in piece
            result = ''
            while(True):
                # Replace one tag
                m = re.search('\\(\\?[<](.+?)[>]\\)', piece)
                if not m:
                    m = re.search('\\\\g[<](.+?)[>]', piece)
                    if not m:
                        result += piece
                        break
                result += piece[:m.start()]
                measurement = '%s_%s' % (C_METADATA, m.groups()[0])
                result += str(self.get_measurement("Image", measurement,
                                                   image_set_number))
                piece = piece[m.end():]
            result_pieces.append(result)
        return single_backquote.join(result_pieces)

    def has_groups(self):
        '''Return True if there is more than one group in the image sets
        
        Note - this works the dumb way now: it fetches all of the group numbers
               and sees if there is a single unique group number. It involves
               fetching the whole column and it doesn't cache, so it could
               be expensive. Alternatively, this could be an experiment
               measurement, populated after prepare_run.
        '''
        if self.has_feature(IMAGE, GROUP_NUMBER):
            image_numbers = self.get_image_numbers()
            if len(image_numbers) > 0:
                group_numbers = self.get_measurement(
                    IMAGE, GROUP_NUMBER,
                    image_set_number = image_numbers)
                return len(np.unique(group_numbers)) > 1
        return False

    def group_by_metadata(self, tags):
        """Return groupings of image sets with matching metadata tags

        tags - a sequence of tags to match.

        Returns a sequence of MetadataGroup objects. Each one represents
        a set of values for the metadata tags along with the image numbers of
        the image sets that match the values
        """
        if len(tags) == 0:
            # if there are no tags, all image sets match each other
            return [MetadataGroup({}, self.get_image_numbers())]

        #
        # The flat_dictionary has a row of tag values as a key
        #
        flat_dictionary = {}
        image_numbers = self.get_image_numbers()
        values = [self.get_measurement(
            IMAGE, "%s_%s" % (C_METADATA, tag), image_numbers)
                  for tag in tags]
        for i, image_number in enumerate(image_numbers):
            key = tuple([(k, v[i]) for k, v in zip(tags, values)])
            if not flat_dictionary.has_key(key):
                flat_dictionary[key] = []
            flat_dictionary[key].append(image_number)
        result = []
        for row in flat_dictionary.keys():
            tag_dictionary = dict(row)
            result.append(MetadataGroup(tag_dictionary, flat_dictionary[row]))
        return result
    
    def match_metadata(self, features, values):
        '''Match vectors of metadata values to existing measurements
        
        This method finds the image sets that match each row in a vector
        of metadata values. Imagine being given an image set with metadata
        values of plate, well and site and annotations for each well
        with metadata values of plate and well and annotation. You'd like
        to match each annotation with all of the sites for it's well. This
        method will return the image numbers that match.
        
        The method can also be used to match images, for instance when
        different illumination correction functions need to be matched
        against plates or sites.
        
        features - the measurement names for the incoming metadata
        
        values - a sequence of vectors, one per feature, giving the
                 metadata values to be matched.

        returns a sequence of vectors of image numbers of equal length
        to the values. An exception is thrown if the metadata for more
        than one row in the values matches the same image set unless the number
        of values in each vector equals the number of image sets - in that case,
        the vectors are assumed to be arranged in the correct order already.
        '''
        #
        # Get image features populated by previous modules. If there are any,
        # then we launch the desperate heuristics that attempt to match
        # to them, either by order or by common metadata
        #
        image_set_count = len(self.get_image_numbers())
        by_order = [[i+1] for i in range(len(values[0]))]
        if image_set_count == 0:
            return by_order
        
        image_features = self.get_feature_names(IMAGE)
        metadata_features = [x for x in image_features
                             if x.startswith(C_METADATA + "_")]
        common_features = [x for x in metadata_features
                           if x in features]
        if len(common_features) == 0:
            if image_set_count > len(values[0]):
                raise ValueError(
                    "The measurements and data have no metadata in common")
            return by_order
        #
        # This reduces numberlike things to integers so that they can be
        # more loosely matched.
        #
        def cast(x):
            if isinstance(x,basestring) and x.isdigit():
                return int(x)
            return x
        
        common_tags = [f[(len(C_METADATA)+1):] for f in common_features]
        groupings = self.group_by_metadata(common_tags)
        groupings = dict([(tuple([cast(d[f]) for f in common_tags]), 
                           d.image_numbers)
                          for d in groupings])
        if image_set_count == len(values[0]):
            #
            # Test whether the common features uniquely identify
            # all image sets. If so, then we can match by metadata
            # and that will be correct, even when the user wants to
            # match by order (assuming the user really did match
            # the metadata)
            #
            if any([len(v) != 1 for v in groupings.values()]):
                return by_order
        #
        # Create a list of values that matches the common_features
        #
        result = []
        vv = [values[features.index(c)] for c in common_features]
        for i in range(len(values[0])):
            key = tuple([cast(vvv[i]) for vvv in vv])
            if not groupings.has_key(key):
                raise ValueError(
                    "There was no image set whose metadata matched row %d.\n"
                    "Metadata values: " +
                    ", ".join(["%s = %s" % (k, v)
                               for k,v in zip(common_features, key)]))
            result.append(groupings[key])
        return result
        
    def agg_ignore_object(self, object_name):
        """Ignore objects (other than 'Image') if this returns true"""
        if object_name in (EXPERIMENT, NEIGHBORS):
            return True

    def agg_ignore_feature(self, object_name, feature_name):
        """Return true if we should ignore a feature during aggregation"""

        if self.agg_ignore_object(object_name):
            return True
        if self.hdf5_dict.has_feature(object_name, "SubObjectFlag"):
            return True
        return agg_ignore_feature(feature_name)

    def compute_aggregate_measurements(self, image_set_number,
                                       aggs=AGG_NAMES):
        """Compute aggregate measurements for a given image set

        returns a dictionary whose key is the aggregate measurement name and
        whose value is the aggregate measurement value
        """
        d = {}
        for object_name in self.get_object_names():
            if object_name == 'Image':
                continue
            for feature in self.get_feature_names(object_name):
                if self.agg_ignore_feature(object_name, feature):
                    continue
                feature_name = "%s_%s" % (object_name, feature)
                values = self.get_measurement(object_name, feature,
                                              image_set_number)
                if values is not None:
                    values = values[np.isfinite(values)]
                #
                # Compute the mean and standard deviation
                #
                if AGG_MEAN in aggs:
                    mean_feature_name = get_agg_measurement_name(
                        AGG_MEAN, object_name, feature)
                    mean = values.mean() if values is not None else np.NaN
                    d[mean_feature_name] = mean
                if AGG_MEDIAN in aggs:
                    median_feature_name = get_agg_measurement_name(
                        AGG_MEDIAN, object_name, feature)
                    median = np.median(values) if values is not None else np.NaN
                    d[median_feature_name] = median
                if AGG_STD_DEV in aggs:
                    stdev_feature_name = get_agg_measurement_name(
                        AGG_STD_DEV, object_name, feature)
                    stdev = values.std() if values is not None else np.NaN
                    d[stdev_feature_name] = stdev
        return d
    
    def load_image_sets(self, fd_or_file, start=None, stop=None):
        '''Load image sets from a .csv file into a measurements file
        
        fd_or_file - either the path name of the .csv file or a file-like object
        
        start - the 1-based image set number to start the loading. For instance,
                for start = 2, we skip the first line and write image
                measurements starting at line 2 into image set # 2
                
        stop - stop loading when this line is reached.
        '''
        if isinstance(fd_or_file, basestring):
            with open(fd_or_file, "r") as fd:
                return self.load_image_sets(fd, start, stop)
        import csv
        reader = csv.reader(fd_or_file)
        header = reader.next()
        columns = [[] for _ in range(len(header))]
        column_is_all_none = np.ones(len(header), bool)
        last_image_number = 0
        for i, fields in enumerate(reader):
            image_number = i + 1
            if start is not None and start < image_number:
                continue
            if stop is not None and image_number == stop:
                break
            for j, (field, column) in enumerate(zip(fields, columns)):
                if field == "None" or len(field) == 0:
                    field = None
                else:
                    column_is_all_none[j] = False
                column.append(field)
            last_image_number = image_number
        if last_image_number == 0:
            logger.warn("No image sets were loaded")
            return
        if start is None:
            image_numbers = list(range(1, last_image_number + 1))
        else:
            image_numbers = list(range(start, last_image_number + 1))
        self.hdf5_dict.add_all(IMAGE, IMAGE_NUMBER, image_numbers, image_numbers)
        for feature, column, all_none in zip(header, columns, column_is_all_none):
            if not all_none:
                # try to convert to an integer, then float, then leave as string
                column = np.array(column, object)
                try:
                    column = column.astype(int)
                except:
                    try:
                        column = column.astype(float)
                    except:
                        pass
                self.hdf5_dict.add_all(IMAGE, feature, column, image_numbers)
                
    def write_image_sets(self, fd_or_file, start = None, stop = None):
        if isinstance(fd_or_file, basestring):
            with open(fd_or_file, "w") as fd:
                return self.write_image_sets(fd, start, stop)
        
        fd = fd_or_file
        
        to_save = [ GROUP_NUMBER, GROUP_INDEX]
        to_save_prefixes = [
            C_URL, C_PATH_NAME, C_FILE_NAME, C_SERIES, C_FRAME,
            C_CHANNEL, C_OBJECTS_URL, C_OBJECTS_PATH_NAME,
            C_OBJECTS_FILE_NAME, C_OBJECTS_SERIES, C_OBJECTS_FRAME,
            C_OBJECTS_CHANNEL, C_METADATA]
        
        keys = []
        image_features = self.get_feature_names(IMAGE)
        for feature in to_save:
            if feature in image_features:
                keys.append(feature)
        for prefix in to_save_prefixes:
            for feature in image_features:
                if feature.startswith(prefix) and feature not in keys:
                    keys.append(feature)
        header = "\""+"\",\"".join(keys) + "\"\n"
        fd.write(header)
        image_numbers = self.get_image_numbers()
        if start is not None:
            image_numbers = [x for x in image_numbers if x >= start]
        if stop is not None:
            image_numbers = [x for x in image_numbers if x <= stop]
            
        if len(image_numbers) == 0:
            return
        
        columns = [self.get_measurement(IMAGE, feature_name, 
                                        image_set_number = image_numbers)
                   for feature_name in keys]
        for i, image_number in enumerate(image_numbers):
            for j, column in enumerate(columns):
                field = column[i]
                if field is None:
                    field = ""
                elif isinstance(field, unicode):
                    field = field.encode("unicode-escape")
                if isinstance(field, basestring):
                    # The unicode character for double quote
                    field = field.replace('"', "\\u0022")
                    field = "\"" + field + "\""
                else:
                    field = str(field)
                if j > 0:
                    fd.write(","+field)
                else:
                    fd.write(field)
            fd.write("\n")
        
    ###########################################################
    #
    # Ducktyping measurements as image sets
    #
    ###########################################################
    
    @property
    def image_number(self):
        '''The image number of the current image'''
        return self.image_set_number
    
    @property
    def get_keys(self):
        '''The keys that uniquely identify the image set
        
        Return key/value pairs for the metadata that specifies the site
        for the image set, for instance, plate / well / site. If image set
        was created by matching images by order, the image number will be
        returned.
        '''
        #
        # XXX (leek) - save the metadata tags used for matching in the HDF
        #              then use it to look up the values per image set
        #              and cache.
        #
        return { IMAGE_NUMBER: str(self.image_number) }
    
    def get_grouping_keys(self):
        '''Get a key, value dictionary that uniquely defines the group
        
        returns a dictionary for the current image set's group where the
        key is the image feature name and the value is the value to match
        in the image measurements.
        
        Note: this is somewhat legacy, from before GROUP_NUMBER was defined
              and the only way to determine which images were in a group
              was to get the metadata colums used to define groups and scan
              them for matches. Now, we just return { GROUP_NUMBER: value }
        '''
        return { GROUP_NUMBER: 
                 self.get_current_image_measurement(GROUP_NUMBER) }
    
    def get_image(self, name, 
                  must_be_binary = False,
                  must_be_color = False,
                  must_be_grayscale = False,
                  must_be_rgb = False,
                  cache = True):
        """Return the image associated with the given name
        
        name - name of the image within the image_set
        must_be_color - raise an exception if not a color image
        must_be_grayscale - raise an exception if not a grayscale image
        must_be_rgb - raise an exception if 2-d or if # channels not 3 or 4,
                      discard alpha channel.
        """
        from .modules.loadimages import LoadImagesImageProviderURL
        from .cpimage import GrayscaleImage, RGBImage
        name = str(name)
        if self.__images.has_key(name):
            image  = self.__images[name]
        else:
            matching_providers = [p for p in self.__image_providers
                                  if p.get_name() == name]
            if len(matching_providers) == 0:
                #
                # Try looking up the URL in measurements
                #
                url_feature_name = "_".join((C_URL, name))
                series_feature_name = "_".join((C_SERIES, name))
                index_feature_name = "_".join((C_FRAME, name))
                if not self.has_feature(IMAGE, url_feature_name):
                    raise ValueError("The %s image is missing from the pipeline."%(name))
                # URL should be ASCII only
                url = str(self.get_current_image_measurement(url_feature_name))
                if self.has_feature(IMAGE, series_feature_name):
                    series = self.get_current_image_measurement(
                        series_feature_name)
                else:
                    series = None
                if self.has_feature(IMAGE, index_feature_name):
                    index = self.get_current_image_measurement(
                        index_feature_name)
                else:
                    index = None
                #
                # XXX (leek): Rescale needs to be bubbled up into 
                #             NamesAndTypes and needs to be harvested
                #             from LoadImages etc.
                #             and stored in the measurements.
                #
                rescale = True
                provider = LoadImagesImageProviderURL(
                    name, url, rescale, series, index)
                self.__image_providers.append(provider)
                matching_providers.append(provider)
            image = matching_providers[0].provide_image(self)
            if cache:
                self.__images[name] = image
        if must_be_binary and image.pixel_data.ndim == 3:
            raise ValueError("Image must be binary, but it was color")
        if must_be_binary and image.pixel_data.dtype != np.bool:
            raise ValueError("Image was not binary")
        if must_be_color and image.pixel_data.ndim != 3:
            raise ValueError("Image must be color, but it was grayscale")
        if (must_be_grayscale and 
            (image.pixel_data.ndim != 2)):
            pd = image.pixel_data
            if pd.shape[2] >= 3 and\
               np.all(pd[:,:,0]==pd[:,:,1]) and\
               np.all(pd[:,:,0]==pd[:,:,2]):
                return GrayscaleImage(image)
            raise ValueError("Image must be grayscale, but it was color")
        if must_be_grayscale and image.pixel_data.dtype.kind == 'b':
            return GrayscaleImage(image)
        if must_be_rgb:
            if image.pixel_data.ndim != 3:
                raise ValueError("Image must be RGB, but it was grayscale")
            elif image.pixel_data.shape[2] not in (3,4):
                raise ValueError("Image must be RGB, but it had %d channels" %
                                 image.pixel_data.shape[2])
            elif image.pixel_data.shape[2] == 4:
                logger.warning("Discarding alpha channel.")
                return RGBImage(image)
        return image
    
    def get_providers(self):
        """The list of providers (populated during the image discovery phase)"""
        return self.__image_providers
    
    providers = property(get_providers)
    
    def get_image_provider(self, name):
        """Get a named image provider
        
        name - return the image provider with this name
        """
        providers = filter(lambda x: x.name == name, self.__image_providers)
        assert len(providers)>0, "No provider of the %s image"%(name)
        assert len(providers)==1, "More than one provider of the %s image"%(name)
        return providers[0]
    
    def remove_image_provider(self, name):
        """Remove a named image provider
        
        name - the name of the provider to remove
        """
        self.__image_providers = filter(lambda x: x.name != name, 
                                        self.__image_providers)
        
    def clear_image(self, name):
        '''Remove the image memory associated with a provider
        
        name - the name of the provider
        '''
        self.get_image_provider(name).release_memory()
        if self.__images.has_key(name):
            del self.__images[name]
            
    def clear_cache(self):
        '''Remove all of the cached images'''
        self.__images.clear()
    
    def get_names(self):
        """Get the image provider names
        """
        return [provider.name for provider in self.providers]
    
    names = property(get_names)
    
    def add(self, name, image):
        from .cpimage import VanillaImageProvider
        old_providers = [provider for provider in self.providers
                         if provider.name == name]
        if len(old_providers) > 0:
            self.clear_image(name)
        for provider in old_providers:
            self.providers.remove(provider)
        provider = VanillaImageProvider(name,image)
        self.providers.append(provider)
        
    def set_channel_descriptors(self, channel_descriptors):
        '''Write the names and data types of the channel descriptors
        
        channel_descriptors - pipeline channel descriptors describing the
                              channels in the image set.
        '''
        for iscd in channel_descriptors:
            feature = "_".join((C_CHANNEL_TYPE, iscd.name))
            self.add_experiment_measurement(feature, iscd.channel_type)
        
    def get_channel_descriptors(self):
        '''Read the channel descriptors
        
        Returns pipeline.ImageSetChannelDescriptor instances for each
        channel descriptor specified in the experiment measurements.
        '''
        from cellprofiler.pipeline import Pipeline
        ImageSetChannelDescriptor = Pipeline.ImageSetChannelDescriptor
        iscds = []
        for feature_name in self.get_feature_names(EXPERIMENT):
            if feature_name.startswith(C_CHANNEL_TYPE):
                channel_name = feature_name[(len(C_CHANNEL_TYPE)+1):]
                channel_type = self.get_experiment_measurement(feature_name)
                if channel_type == ImageSetChannelDescriptor.CT_OBJECTS:
                    url_feature = "_".join([C_OBJECTS_URL, channel_name])
                else:
                    url_feature = "_".join([C_URL, channel_name])
                if url_feature not in self.get_feature_names(IMAGE):
                    continue
                iscds.append(ImageSetChannelDescriptor(channel_name, channel_type))
        return iscds
    
    def set_metadata_tags(self, metadata_tags):
        '''Write the metadata tags that are used to make an image set
        
        metadata_tags - image feature names of the metadata tags that uniquely
                        define an image set. If metadata matching wasn't used,
                        write the image number feature name.
        '''
        data = json.dumps(metadata_tags)
        self.add_experiment_measurement(M_METADATA_TAGS, data)
        
    def get_metadata_tags(self):
        '''Read the metadata tags that are used to make an image set
        
        returns a list of metadata tags
        '''
        if M_METADATA_TAGS not in self.get_feature_names(EXPERIMENT):
            return [ IMAGE_NUMBER ]
        return json.loads(self.get_experiment_measurement(M_METADATA_TAGS))

def load_measurements_from_buffer(buf):
    dir = cpprefs.get_default_output_directory()
    if not (os.path.exists(dir) and os.access(dir, os.W_OK)):
        dir = None
    fd, filename = tempfile.mkstemp(prefix='Cpmeasurements', suffix='.hdf5', dir=dir)
    os.write(fd, buf)
    os.close(fd)
    try:
        return load_measurements(filename)
    finally:
        os.unlink(filename)

def load_measurements(filename, dest_file = None, can_overwrite = False,
                      run_name = None):
    '''Load measurements from an HDF5 file
    
    filename - path to file containing the measurements or file-like object
               if .mat
    
    dest_file - path to file to be created. This file is used as the backing
                store for the measurements.
                
    can_overwrite - True to allow overwriting of existing measurements (not
                    supported any longer)
                    
    run_name - name of the run (an HDF file can contain measurements
               from multiple runs). By default, takes the last.
    
    returns a Measurements object
    '''
    HDF5_HEADER = (chr(137) + chr(72) + chr(68) + chr(70) + chr(13) + chr(10) +
                   chr (26) + chr(10))
    if hasattr(filename, "seek"):
        filename.seek(0)
        header = filename.read(len(HDF5_HEADER))
        filename.seek(0)
    else:
        fd = open(filename, "rb")
        header = fd.read(len(HDF5_HEADER))
        fd.close()

    if header == HDF5_HEADER:
        f, top_level = get_top_level_group(filename)
        try:
            if VERSION in f.keys():
                if run_name is not None:
                    top_level = top_level[run_name]
                else:
                    # Assume that the user wants the last one
                    last_key = sorted(top_level.keys())[-1]
                    top_level = top_level[last_key]
            m = Measurements(filename=dest_file, copy = top_level)
            return m
        except:
            logger.error("Error loading HDF5 %s", filename, exc_info=True)
        finally:
            f.close()
    else:
        m = Measurements(filename = dest_file)
        m.load(filename)
        return m

class MetadataGroup(dict):
    """A set of metadata tag values and the image set indexes that match

    The MetadataGroup object represents a group of image sets that
    have the same values for a given set of tags. For instance, if an
    experiment has metadata tags of "Plate", "Well" and "Site" and
    we form a metadata group of "Plate" and "Well", then each metadata
    group will have image set indexes of the images taken of a particular
    well
    """
    def __init__(self, tag_dictionary, image_numbers):
        super(MetadataGroup, self).__init__(tag_dictionary)
        self.__image_numbers = image_numbers

    @property
    def image_numbers(self):
        return self.__image_numbers

    def __setitem__(self, tag, value):
        raise NotImplementedError("The dictionary is read-only")

def find_metadata_tokens(pattern):
    """Return a list of strings which are the metadata token names in a pattern

    pattern - a regexp-like pattern that specifies how to find
              metadata in a string. Each token has the form:
              "(?<METADATA_TAG>...match-exp...)" (matlab-style) or
              "\g<METADATA_TAG>" (Python-style replace)
              "(?P<METADATA_TAG>...match-exp..)" (Python-style search)
    """
    result = []
    while True:
        m = re.search('\\(\\?[<](.+?)[>]', pattern)
        if not m:
            m = re.search('\\\\g[<](.+?)[>]', pattern)
            if not m:
                m = re.search('\\(\\?P[<](.+?)[>]', pattern)
                if not m:
                    break
        result.append(m.groups()[0])
        pattern = pattern[m.end():]
    return result

def extract_metadata(pattern, text):
    """Return a dictionary of metadata extracted from the text

    pattern - a regexp that specifies how to find
              metadata in a string. Each token has the form:
              "\(?<METADATA_TAG>...match-exp...\)" (matlab-style) or
              "\(?P<METADATA_TAG>...match-exp...\)" (Python-style)
    text - text to be searched

    We do a little fixup in here to change Matlab searches to Python ones
    before executing.
    """
    # Convert Matlab to Python
    orig_pattern = pattern
    pattern = re.sub('(\\(\\?)([<].+?[>])', '\\1P\\2', pattern)
    match = re.search(pattern, text)
    if match:
        return match.groupdict()
    else:
        raise ValueError("Metadata extraction failed: regexp '%s' does not match '%s'" % (orig_pattern, text))

def is_well_row_token(x):
    '''True if the string represents a well row metadata tag'''
    return x.lower() in ("wellrow", "well_row", "row")

def is_well_column_token(x):
    '''true if the string represents a well column metadata tag'''
    return x.lower() in ("wellcol", "well_col", "wellcolumn", "well_column",
                         "column", "col")

def get_agg_measurement_name(agg, object_name, feature):
    '''Return the name of an aggregate measurement

    agg - one of the names in AGG_NAMES, like AGG_MEAN
    object_name - the name of the object that we're aggregating
    feature - the name of the object's measurement
    '''
    return "%s_%s_%s" % (agg, object_name, feature)

def agg_ignore_feature(feature_name):
    '''Return True if the feature is one to be ignored when aggregating'''
    if feature_name.startswith('Description_'):
        return True
    if feature_name.startswith('ModuleError_'):
        return True
    if feature_name.startswith('TimeElapsed_'):
        return True
    if feature_name == "Number_Object_Number":
        return True
    return False

class RelationshipKey:
    def __init__(self, module_number, group_number, relationship,
                 object_name1, object_name2):
        self.module_number = module_number
        self.group_number = group_number
        self.relationship = relationship
        self.object_name1 = object_name1
        self.object_name2 = object_name2
