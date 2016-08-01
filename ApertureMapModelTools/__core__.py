"""
This stores the basic class and function dependencies of the
ApertureMapModelTools module.
#
Written By: Matthew Stadelman
Date Written: 2016/02/26
Last Modifed: 2016/06/10
#
"""
#
########################################################################
#
import subprocess
import re
import os
import scipy as sp
from scipy import sparse as sprs
#
########################################################################
#  Basic classes
########################################################################


class ArgProcessor:
    r"""
    Generalizes the processing of an input argument
    """

    def __init__(self, field,
                 map_func=lambda x: x,
                 min_num_vals=1,
                 out_type='single',
                 expected='str',
                 err_desc_str='to have a value'):
        #
        self.field = field
        self.map_func = map_func
        self.min_num_vals = min_num_vals
        self.out_type = out_type
        self.expected = expected
        self.err_desc_str = err_desc_str


class DataField:
    r"""
    Base class to store raw data from a 2-D field data file and
    the output data generated by the different processing routines
    """
    def __init__(self, infile, **kwargs):
        self.infile = infile
        self.outfile = ''
        self.nx = 0
        self.nz = 0
        self._raw_data = None
        self.data_map = None
        self.data_vector = None
        self.point_data = None
        self._cell_interfaces = None
        self.output_data = dict()
        #
        if infile is not None:
            self.parse_data_file(**kwargs)

    def clone(self):
        r"""
        Creates a fully qualified DataField object from the existing one.
        """
        # instantiating class and adding attributes
        clone = DataField(None)
        #
        self.copy_data(clone)
        clone._raw_data = sp.copy(self._raw_data)
        clone._cell_interfaces = sp.copy(self._cell_interfaces)
        #
        return clone

    def copy_data(self, obj):
        r"""
        Copies data properites of the field onto another object created
        """
        obj.nx = self.nx
        obj.nz = self.nz
        obj.data_map = sp.copy(self.data_map)
        obj.data_vector = sp.copy(self.data_vector)
        obj.point_data = sp.copy(self.point_data)

    def parse_data_file(self, delim='auto', **kwargs):
        r"""
        Reads the field's infile data and then populates the data_map array
        and sets the fields nx and nz properties.
        """
        #
        if delim == 'auto':
            with open(self.infile, 'r') as file:
                line = file.readline()
                #
                pat = r'[-0-9.+eE]+([^-0-9.+eE]+)[-0-9.+eE]+'
                match = re.search(pat, line)
                delim = match.group(1).strip()
                delim = None if not delim else delim
        #
        self.data_map = sp.loadtxt(self.infile, delimiter=delim)
        self._raw_data = sp.copy(self.data_map)
        self.data_vector = sp.ravel(self.data_map)
        self.nz, self.nx = self.data_map.shape
        #
        # defining cell interfaces used in adjacency matrix
        self._define_cell_interfaces()

    def _define_cell_interfaces(self):
        r"""
        Populates the cell_interfaces array
        """
        # covering right column
        self._cell_interfaces = []
        for iz in range(self.nx-1, (self.nz-1)*self.nx, self.nx):
            self._cell_interfaces.append([iz, iz+self.nx])
        # covering interior cells
        for iz in range(0, self.nz-1):
            for ix in range(0, self.nx-1):
                ib = iz*self.nx + ix
                self._cell_interfaces.append([ib, ib+1])
                self._cell_interfaces.append([ib, ib+self.nx])
        # covering top row
        for ix in range((self.nz-1)*self.nx, self.nz*self.nx-1):
            self._cell_interfaces.append([ix, ix+1])
        #
        self._cell_interfaces = sp.array(self._cell_interfaces,
                                         ndmin=2,
                                         dtype=int)

    def create_adjacency_matrix(self, data=None):
        r"""
        Returns a weighted adjacency matrix, in CSR format based on the
        product of weight values sharing an interface.
        """
        #
        if data is None:
            data = self.data_vector
        #
        weights = data[self._cell_interfaces[:, 0]]
        weights = 2*weights * data[self._cell_interfaces[:, 1]]
        #
        # clearing any zero-weighted connections
        indices = weights > 0
        interfaces = self._cell_interfaces[indices]
        weights = weights[indices]
        #
        # getting cell connectivity info
        row = interfaces[:, 0]
        col = interfaces[:, 1]
        #
        # append row & col to each other, and weights to itself
        row = sp.append(row, interfaces[:, 1])
        col = sp.append(col, interfaces[:, 0])
        weights = sp.append(weights, weights)
        #
        # Generate sparse adjacency matrix in 'coo' format and convert to csr
        num_blks = self.nx*self.nz
        matrix = sprs.coo_matrix((weights, (row, col)), (num_blks, num_blks))
        matrix = matrix.tocsr()
        return matrix

    def create_point_data(self):
        r"""
        The data_map attribute stores the cell data read in from file.
        This function takes that cell data and calculates average values
        at the corners to make a point data map. The Created array is 3-D with
        the final index corresponding to corners.
        Index Locations: 0 = BLC, 1 = BRC, 2 = TRC, 3 = TLC
        """
        #
        self.point_data = sp.zeros((self.nz+1, self.nx+1, 4))
        #
        # setting corners of map first
        self.point_data[0, 0, 0] = self.data_map[0, 0]
        self.point_data[0, -1, 1] = self.data_map[0, -1]
        self.point_data[-1, -1, 2] = self.data_map[-1, -1]
        self.point_data[-1, 0, 3] = self.data_map[-1, 0]
        #
        # calculating point values for the map interior
        for iz in range(self.nz):
            for ix in range(self.nx):
                val = sp.average(self.data_map[iz:iz+2, ix:ix+2])
                self.point_data[iz, ix, 2] = val
                self.point_data[iz+1, ix+1, 0] = val
                self.point_data[iz+1, ix, 1] = val
                self.point_data[iz, ix+1, 3] = val
        #
        # handling left and right edges
        for iz in range(self.nz):
            val = sp.average(self.data_map[iz:iz+2, 0])
            self.point_data[iz, 0, 3] = val
            self.point_data[iz+1, 0, 0] = val
            #
            val = sp.average(self.data_map[iz:iz+2, -1])
            self.point_data[iz, -1, 2] = val
            self.point_data[iz+1, -1, 1] = val
        #
        # handling top and bottom edges
        for ix in range(self.nx):
            val = sp.average(self.data_map[0, ix:ix+2])
            self.point_data[0, ix, 1] = val
            self.point_data[0, ix+1, 0] = val
            #
            val = sp.average(self.data_map[-1, ix:ix+2])
            self.point_data[-1, ix, 2] = val
            self.point_data[-1, ix+1, 3] = val
        #
        self.point_data = self.point_data[0:self.nz, 0:self.nx, :]

    def threshold_data(self, min_value=None, max_value=None, repl=sp.nan):
        r"""
        Thresholds the data map based on the supplied minimum and
        maximum values. Values outside of the range are replaced by
        the repl argument which defaults to sp.nan.
        """
        #
        if min_value is not None:
            self.data_map[self.data_map <= min_value] = repl
        if max_value is not None:
            self.data_map[self.data_map >= max_value] = repl
        #
        # updating linked attributes
        self.data_vector = sp.ravel(self.data_map)


class StatFile:
    r"""
    Parses and stores information from a simulation statisitics file. This
    class helps facilitate data mining of simulation results.
    """

    def __init__(self, infile):
        self.infile = infile
        self.map_file = ''
        self.pvt_file = ''
        self.data_dict = {}
        self.unit_dict = {}
        self.parse_stat_file()

    def parse_stat_file(self, stat_file=None):
        r"""
        Parses either the supplied infile or the class's infile and
        uses the data to populate the data_dict.
        """
        self.infile = (stat_file if stat_file else self.infile)
        #
        with open(self.infile, 'r') as f:
            content = f.read()
            content_arr = content.split('\n')
            content_arr = [re.sub(r', *$', '', l).strip() for l in content_arr]
            content_arr = [re.sub(r'^#.*', '', l) for l in content_arr]
            content_arr = [l for l in content_arr if l]
        #
        map_file_line = content_arr.pop(0)
        pvt_file_line = content_arr.pop(0)
        #
        # adding the space prevents a possible index error
        self.map_file = re.split(r'\s', map_file_line+' ', 1)[1]
        self.pvt_file = re.split(r'\s', pvt_file_line+' ', 1)[1]
        #
        # stepping through pairs of lines to get key -> values
        for i in range(0, len(content_arr), 2):
            key_arr = re.split(r',', content_arr[i])
            val_arr = re.split(r',', content_arr[i+1])
            key_list = [k.strip() for k in key_arr]
            val_list = [float(v) for v in val_arr]
            #
            for key, val in zip(key_list, val_list):
                m = re.search(r'\[(.*?)\]$', key)
                unit = (m.group(1) if m else '-')
                key = re.sub(r'\[.*?\]$', '', key).strip()
                self.data_dict[key] = val
                self.unit_dict[key] = unit

#
########################################################################
#  Base functions
########################################################################


def files_from_directory(directory='.', pattern='.', deep=True):
    r"""
    Allows the user to get a list of files in the supplied directory
    matching a regex pattern. If deep is set to True then any
    sub-directories found will also be searched. A pre-compiled pattern
    can be supplied instead of a string.
    """
    #
    # setting up pattern
    try:
        if (pattern[0] == '*'):
            pattern = re.sub(r'\.', r'\\.', pattern)
            pattern = '.'+pattern+'$'
            print('Modifying glob pattern to proper regular expression', pattern)
        pattern = re.compile(pattern, flags=re.I)
    except (ValueError, TypeError):
        print('Using user compiled pattern: ', pattern)
    #
    # initializing
    dirs = [directory]
    files = []
    while dirs:
        #
        directory = dirs.pop(0)
        cmd_arr = ['ls', directory]
        ls = subprocess.Popen(cmd_arr,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True)
        std_out, std_err = ls.communicate()
        content_arr = std_out.split('\n')
        content_arr = [c.strip() for c in content_arr if c.strip()]
        #
        for path in content_arr:
            pth = os.path.join(directory, path)
            pth = os.path.realpath(pth)
            if os.path.isdir(pth) and deep:
                dirs.append(str(pth))
            elif os.path.isfile(pth) and pattern.search(pth):
                files.append(pth)
    #
    return files


def load_infile_list(infile_list, delim='auto'):
    r"""
    Function to generate a list of DataField objects from a list of input files
    """
    field_list = []
    #
    # loading and parsing each input file
    for infile in infile_list:
        #
        # constructing object
        field = DataField(infile)
        print('Finished reading file: '+field.infile)
        #
        field_list.append(field)
    #
    return(field_list)


def calc_percentile(perc, data, sort=True):
    r"""
    Calculates the desired percentile of a dataset.
    """
    tot_vals = float(len(data))
    num_vals = 0.0
    sorted_data = list(data)
    if (sort):
        sorted_data.sort()
    #
    # stepping through list
    index = 0
    for i in range(len(sorted_data)):
        index = i
        if ((num_vals/tot_vals*100.0) >= perc):
            break
        else:
            num_vals += 1
    #
    #
    return sorted_data[index]


def calc_percentile_num(num, data, last=False, sort=True):
    r"""
    Calculates the percentile of a provided number in the dataset.
    If last is set to true then the last occurance of the number
    is taken instead of the first.
    """
    tot_vals = float(len(data))
    num_vals = 0.0
    sorted_data = list(data)
    if (sort):
        sorted_data.sort()
    #
    # stepping through list
    for i in range(len(sorted_data)):
        if (last is True) and (data[i] > num):
            break
        elif (last is False) and (data[i] >= num):
            break
        else:
            num_vals += 1
    #
    perc = num_vals/tot_vals
    #
    return perc


def get_data_vect(data_map, direction, start_id=1):
    r"""
    Returns either of a row or column of cells as a vector in the x or z direction
    """
    #
    nz, nx = data_map.shape
    if (direction.lower() == 'x'):
        # getting row index
        if (start_id >= nz):
            start_id = nz
        elif (start_id <= 0):
            start_id = 1
        return data_map[start_id-1, :]

    elif (direction.lower() == 'z'):
        if (start_id >= nx):
            start_id = nx
        elif (start_id <= 0):
            start_id = 1
        #
        return data_map[:, start_id-1]
    else:
        raise ValueError("Error - invalid direction supplied, can only be x or z")


def multi_output_columns(data_fields):
    r"""
    Takes the content of several fields of output data and outputs them
    columnwise side by side
    """
    msg = 'This function is retired until I make a better version'
    raise NotImplementedError(msg)
    #   splitting content of each outfile
    # num_lines = 0
    # for field in data_fields:
    #     content_arr = field.outfile_content.split('\n')
    #     field.outfile_arr = list(content_arr)
    #  num_lines = len(content_arr) if (len(content_arr) > num_lines) else num_lines
    #   processing content
    # content_arr = []
    # max_len = 0
    # for l in range(num_lines):
    #     line_arr = []
    #     for field in data_fields:
    #         try:
    #             line = field.outfile_arr[l].split(',')
    #             max_len = len(line) if (len(line) > max_len) else max_len
    #         except IndexError:
    #             line = ['']
    #         line_arr.append(line)
    #     content_arr.append(line_arr)
    #
    #   creating group content
    # group_content = ''
    # for l in range(len(content_arr)):
    #     line = list(content_arr[l])
    #     out_str = ''
    #     for i in range(len(line)):
    #         for j in range(max_len):
    #             if (j < len(line[i])):
    #                 out_str += line[i][j]+','
    #             else:
    #                 out_str += ','
    #         out_str += ','
    #     group_content += out_str + '\n'
    # return group_content
