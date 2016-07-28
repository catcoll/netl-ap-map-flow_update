"""
Handles testing of the OpenFOAM export module
#
Written By: Matthew Stadelman
Date Written: 2016/06/09
Last Modifed: 2016/06/10
#
"""
#
import os
import pytest
from ApertureMapModelTools.OpenFoamExport.OpenFoamExport import OpenFoamObject
from ApertureMapModelTools import OpenFoamExport as ofe


class TestOpenFoamExport:
    r"""
    Executes a set of functions to handle testing of the export routines
    """
    def setup_class(self):
        pass

    def test_open_foam_object(self):
        of_object = OpenFoamObject()
        with pytest.raises(NotImplementedError):
            print(of_object)

    def test_openfoam_dict(self):
        init_vals = [('key1', 'val1'), ('key2', 'val2'), ('key3', 'val3')]
        of_dict = ofe.OpenFoamDict('testDict', values=init_vals)
        assert of_dict.name == 'testDict'
        assert list(of_dict.items()) == init_vals
        #
        # adding a nested dict
        of_dict['nestedDict'] = ofe.OpenFoamDict('nestedDict', of_dict)
        #
        print(of_dict)

    def test_openfoam_list(self):
        init_vals = ['val1', 'val2', 'val3']
        of_list = ofe.OpenFoamList('testList', values=init_vals)
        assert of_list.name == 'testList'
        assert of_list == init_vals
        #
        # adding a nested list
        of_list.append(ofe.OpenFoamList('nestedList', of_list))
        #
        print(of_list)

    def test_open_foam_file(self):
        init_vals = [('key1', 'val1'), ('key2', 'val2'), ('key3', 'val3')]
        of_file = ofe.OpenFoamFile('test_location', 'test_object', class_name='test_class', values=init_vals)
        #
        # checking initialization
        assert of_file.head_dict['class'] == 'test_class'
        assert of_file.head_dict['location'] == '"test_location"'
        assert of_file.head_dict['object'] == 'test_object'
        assert list(of_file.items()) == init_vals
        #
        # adding  dict and list
        of_file['dict'] = ofe.OpenFoamDict('dict', init_vals)
        of_file['list'] = ofe.OpenFoamList('list', ['val1', 'val2', 'val3'])
        print(of_file)
        #
        # writing file
        of_file.write_foam_file(TEMP_DIR, create_dirs=True, overwrite=False)
        with pytest.raises(FileExistsError):
            of_file.write_foam_file(TEMP_DIR, create_dirs=True, overwrite=False)
        #
        # reading a file
        path = os.path.join(FIXTURE_DIR, 'testFoamFile')
        of_file = ofe.OpenFoamFile.init_from_file(path)
        print(of_file)
        #
        assert of_file.head_dict['object'] == 'testFoamFile'
        assert of_file['keyword1'] == 'value1'
        assert isinstance(of_file['toplevel_dict'], ofe.OpenFoamDict)
        assert isinstance(of_file['toplevel_list'], ofe.OpenFoamList)
        assert len(of_file['toplevel_dict'].keys()) == 6
        assert len(of_file['toplevel_list']) == 5
        assert of_file['toplevel_dict']['nest_dict3']['n3keyword3'] == 'n3value3'
        assert of_file['toplevel_list'][3][1] == 'n4value2'
        #
        # commented out stuff
        with pytest.raises(KeyError):
            of_file['inline_cmt_keyword'] is not None
        with pytest.raises(KeyError):
            of_file['toplevel_dict2'] is not None
        #
        # invalid file
        with pytest.raises(ValueError):
            path = os.path.join(FIXTURE_DIR, 'TEST_INIT.INP')
            of_file = ofe.OpenFoamFile.init_from_file(path)

    def test_block_mesh_dict(self, data_field_class):
        self._field = data_field_class()
        #
        params = {
            'convertToMeters': '0.000010000',
            'numbersOfCells': '(5 10 15)',
            'cellExpansionRatios': 'simpleGrading (1 2 3)',
            #
            'boundary.left.type': 'empty',
            'boundary.right.type': 'empty',
            'boundary.top.type': 'wall',
            'boundary.bottom.type': 'wall',
            'boundary.front.type': 'wall',
            'boundary.back.type': 'wall'
        }
        mesh = ofe.BlockMeshDict(self._field, avg_fact=10.0, mesh_params=params)
        mesh._edges = ['placeholder']
        mesh._mergePatchPairs = ['placeholder']
        mesh.write_foam_file(TEMP_DIR, overwrite=True)
        #
        # attempting to overwrite existing mesh file
        with pytest.raises(FileExistsError):
            mesh.write_mesh_file(TEMP_DIR, overwrite=False)
        #
        # writing out a symmetry plane
        mesh.write_symmetry_plane(TEMP_DIR, overwrite=True)

    def test_open_foam_export(self, data_field_class):
        self._field = data_field_class()
        #
        export = ofe.OpenFoamExport(field=self._field)
        #
        test_file = [
            ('location', 'test'),
            ('object', 'testFile'),
            ('key1', 'val1'),
            ('key2', 'val2'),
        ]
        #
        export.generate_foam_files(test_file)
        assert export.foam_files['test.testFile']
        assert export.foam_files['test.testFile']['key1'] == 'val1'
        assert list(export.foam_files['test.testFile'].keys()) == ['key1', 'key2']
        #
        export.write_mesh_file(TEMP_DIR, create_dirs=True, overwrite=True)
        export.write_symmetry_plane(TEMP_DIR, create_dirs=True, overwrite=True)
        export.write_foam_files(TEMP_DIR, overwrite=True)
        with pytest.raises(FileExistsError):
            export.write_foam_files(TEMP_DIR, overwrite=False)
