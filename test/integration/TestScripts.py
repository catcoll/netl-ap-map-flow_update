"""
Handles testing of the script files when running setup.py
#
Written By: Matthew Stadelman
Date Written: 2017/04/09
Last Modifed: 2017/04/09
#
"""
from glob import glob
import os
import pytest
import re
from subprocess import Popen, PIPE, check_output
import yaml
import ApertureMapModelTools as amt


def check_path(*args):
    r"""
    runs an assertion that the file exists
    """
    assert os.path.isfile(os.path.join(*args))


@pytest.mark.usefixtures('script_directory')
class TestScripts:
    r"""
    Manages running the test suite
    """

    def run_script(cls, script, args):
        r"""
        runs the set of args provided for the script
        """,
        script = os.path.join(SCRIPT_DIR, script)
        cmd = ['python', script] + args
        proc = Popen(cmd)
        print('Running command: ', cmd)
        assert not proc.wait()

    def test_apm_bulk_run(cls):
        # load bulk run file for pre-processing
        bulkrun_inp_file = os.path.join(FIXTURE_DIR, 'test-bulk-run.yaml')
        with open(bulkrun_inp_file, 'r') as f:
            bulk_run_inps = yaml.load(f)
        #
        # update paths to be platform independent
        file_path = bulk_run_inps['initial_input_file']
        bulk_run_inps['initial_input_file'] = os.path.join(FIXTURE_DIR, file_path)
        for key, file_path in bulk_run_inps['default_file_formats'].items():
            if key == 'APER-MAP':
                file_path = os.path.join(FIXTURE_DIR, 'maps', file_path)
            else:
                file_path = os.path.join(TEMP_DIR, file_path)
            #
            bulk_run_inps['default_file_formats'][key] = file_path
        #
        # output the file
        bulkrun_inp_file = os.path.join(TEMP_DIR, 'test-bulk-run.yaml')
        with open(bulkrun_inp_file, 'w') as f:
            f.write(yaml.dump(bulk_run_inps))
        #
        # run dry run
        args = ['-v', bulkrun_inp_file]
        cls.run_script('apm-bulk-run.py', args)
        #
        # actually perform bulk run
        args = ['-v', '--start', bulkrun_inp_file]
        cls.run_script('apm-bulk-run.py', args)
        #
        # checking that some files were created
        assert os.path.isfile(os.path.join(TEMP_DIR,
                              'parallel-plate-01vox-RF1.00-400PA-STAT.csv'))
        assert os.path.isfile(os.path.join(TEMP_DIR,
                              'parallel-plate-01vox-RF1.00-400PA-STAT.yaml'))
        assert os.path.isfile(os.path.join(TEMP_DIR,
                              'parallel-plate-10vox-RF1.00-700PA-LOG.TXT'))
        assert os.path.isfile(os.path.join(TEMP_DIR,
                              'Fracture1ApertureMap-10avg-RF0.00-300PA-INIT.INP'))

    def test_fracture_df(cls):
        # run dry run -xz --bot --mid --top
        infile = os.path.join(FIXTURE_DIR, 'binary-fracture-small.tif')
        args = ['-xz', '--bot', '--mid', '--top', infile, '-o', TEMP_DIR]
        cls.run_script('apm-fracture-df.py', args)
        #
        # check that file was created
        assert os.path.isfile(os.path.join(TEMP_DIR, 'binary-fracture-small-df.txt'))

    def test_convert_csv_stats_file(cls):
        #
        # run dry run -xz --bot --mid --top
        infile = os.path.join(FIXTURE_DIR, 'legacy-stats-file.csv')
        args = ['-v', infile, '-o', TEMP_DIR]
        cls.run_script('apm-convert-csv-stats-file.py', args)
        #
        assert os.path.isfile(os.path.join(TEMP_DIR, 'legacy-stats-file.yaml'))

    def test_generate_aperture_map(cls):
        #
        infile = os.path.join(FIXTURE_DIR, 'binary-fracture.tif')
        args = ['-v', '--gen-colored-stack', infile, '-o', TEMP_DIR]
        cls.run_script('apm-generate-aperture-map.py', args)
        #
        # test for file existance
        filename = 'binary-fracture-aperture-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, filename))
        filename = 'binary-fracture-colored.tif'
        assert os.path.isfile(os.path.join(TEMP_DIR, filename))

    def test_process_image_stack(cls):
        #
        infile = os.path.join(FIXTURE_DIR, 'binary-fracture-small.tif')
        args = ['-vn', '1', '--gen-cluster-img', '-o', TEMP_DIR, infile]
        cls.run_script('apm-process-image-stack.py', args)
        #
        # test for file existance
        outfile = 'binary-fracture-small-aperture-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))
        outfile = 'binary-fracture-small-offset-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))
        outfile = 'binary-fracture-small-processed.tif'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))

    def test_process_paraview_data(cls):
        #
        infile = os.path.join(FIXTURE_DIR, 'paraview-data-file.csv')
        aper_map = 'Fracture1ApertureMap-10avg.txt'
        aper_map = os.path.join(FIXTURE_DIR, 'maps', aper_map)
        #
        args = ['-v', '--rho', '1000.0', infile, aper_map,
                '2.76e-5', '10', '-o', TEMP_DIR]
        cls.run_script('apm-process-paraview-data.py', args)
        #
        outfile = 'paraview-data-file-p-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))
        outfile = 'paraview-data-file-qx-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))
        outfile = 'paraview-data-file-qz-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))
        outfile = 'paraview-data-file-qm-map.txt'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))

    def test_resize_image_stack(cls):
        #
        infile = os.path.join(FIXTURE_DIR, 'binary-fracture-small.tif')
        args = ['-v', infile, '-o', TEMP_DIR]
        cls.run_script('apm-resize-image-stack.py', args)
        #
        outfile = 'binary-fracture-small-resized.tif'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))

    def test_run_lcl_model(cls):
        #
        inp_file = os.path.join(FIXTURE_DIR, 'test-model-inputs.txt')
        infile = 'model-input-file.inp'
        inp_file = amt.RunModel.InputFile(inp_file, {'input_file': infile})
        #
        # adding aperture map
        infile = 'Fracture1ApertureMap-10avg.txt'
        inp_file['APER-MAP'] = os.path.join(FIXTURE_DIR, 'maps', infile)
        #
        # updating file paths
        files = {}
        for key, arg in inp_file.items():
            if re.search(r'FILE$', key):
                files[key] = os.path.join(TEMP_DIR, arg.value)
                inp_file[key] = files[key]
            if key == 'FLOW-FILE' or key == 'STAT-FILE':
                del files[key]  # deleteing here because file isn't created as is
        #
        inp_file.write_inp_file(alt_path=TEMP_DIR)
        #
        exe_file = os.path.split(amt.__file__)[0]
        exe_file = os.path.join(exe_file, amt.DEFAULT_MODEL_NAME)
        infile = os.path.join(TEMP_DIR, 'model-input-file.inp')
        args = ['-v', '-e', exe_file, infile]
        cls.run_script('apm-run-lcl-model.py', args)
        #
        # test for file existance
        for outfile in files.values():
            assert os.path.isfile(outfile)

    def test_subtract_data_maps(cls):
        #
        map_file = 'coverage_test_aper-orig.csv'
        map_file = os.path.join(TEST_ROOT, 'fortran', 'fixtures', map_file)
        data_file1 = 'coverage_test_flow-x-orig.csv'
        data_file1 = os.path.join(TEST_ROOT, 'fortran', 'fixtures', data_file1)
        data_file2 = 'coverage_test_flow-z-orig.csv'
        data_file2 = os.path.join(TEST_ROOT, 'fortran', 'fixtures', data_file2)
        #
        args = ['-v', '-pn', '-on', '-abs', map_file, data_file1, data_file2,
                'sub-data-file.txt', '-o', TEMP_DIR]
        cls.run_script('apm-subtract-data-maps.py', args)
        #
        # check for file existance
        assert os.path.isfile(os.path.join(TEMP_DIR, 'sub-data-file.txt'))

    def test_combine_yaml_stat_files(cls):
        #
        args = ['-vrp', 'test-stat.*.yaml', TEST_ROOT, '-o', TEMP_DIR]
        cls.run_script('apm-combine-yaml-stat-files.py', args)
        #
        # check for file existance
        outfile = 'combined-fracture-stats.csv'
        assert os.path.isfile(os.path.join(TEMP_DIR, outfile))

    def test_process_data_map(cls):
        script = 'apm-process-data-map.py'
        infile = os.path.join(FIXTURE_DIR, 'flow-map.csv')
        main_args = ['-files', infile, '-o', TEMP_DIR]
        #
        # run eval channels
        args = ['-v', 'chans', 'x', '1e-3'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-channel_data-X-axis.csv')
        #
        args = ['-v', 'chans', 'z', '1e-3'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-channel_data-X-axis.csv')
        #
        # run histogram
        args = ['-v', 'hist', '16'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-histogram.csv')
        #
        # run histogram range
        args = ['-v', 'histrng', '16', '-r', '5', '95'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-histogram_range.csv')
        #
        # run histogram range
        args = ['-v', 'histlog', '5'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-histogram_logscale.csv')
        #
        # run percentile routine
        args = ['-v', 'perc', '10', '50', '90'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-percentiles.csv')
        #
        # run profile routines
        args = ['-v', 'prof', 'x', '10', '50', '90'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-profiles-X-axis.csv')
        #
        args = ['-v', 'prof', 'z', '10', '50', '90'] + main_args
        cls.run_script(script, args)
        check_path(TEMP_DIR, 'flow-map-profiles-Z-axis.csv')
