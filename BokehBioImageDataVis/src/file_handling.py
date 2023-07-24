import logging
import shutil
import uuid
from os import makedirs
from os.path import split, join, basename, splitext, exists, dirname, normpath


def get_folder_structure(filepath, copy_files_dir_level):
    folders = []
    while True:
        filepath, folder = split(filepath)
        if folder != "":
            folders.append(folder)
        else:
            if filepath != "":
                folders.append(filepath)
            break

    wanted_folder_structure = folders[1:1 + copy_files_dir_level]
    return join(*wanted_folder_structure)


def copy_files_to_output_dir(df, path_key, output_folder, used_paths, copy_files_dir_level):
    for src_path in df[path_key].unique():

        if not exists(src_path):
            logging.warning(f'Warning: {src_path} does not exist. Skipping copy.')
            continue

        filename = basename(src_path)
        folder_structure_to_copy = get_folder_structure(src_path, copy_files_dir_level)

        target_path = join(output_folder, 'data', folder_structure_to_copy, filename)
        logging.debug(f'copy {src_path} to {target_path}')

        if target_path in used_paths:
            logging.warning(f'Warning: filename {filename} already used. Adding unique id to filename.')
            filename_no_ext, ext = splitext(filename)
            filename = f'{filename_no_ext}_{uuid.uuid4()}{ext}'
            target_path = join(output_folder, 'data', folder_structure_to_copy, filename)

        used_paths.append(target_path)

        if not exists(dirname(target_path)):
            makedirs(dirname(target_path))

        # check if paths are the same, also incorporating e.g. ./ at the beginning
        if normpath(src_path) == normpath(target_path):
            logging.warning('Warning: src and target path are the same. Skipping copy.')
            continue
        shutil.copyfile(src_path, target_path)

        # update old path to new relative path 'data/...'
        target_path_relative = join('data', folder_structure_to_copy, filename)
        df[path_key] = df[path_key].replace(src_path, target_path_relative)

    return df, used_paths
