import os
import subprocess


def system_call(args, cwd="."):
    print("Running '{}' in '{}'".format(str(args), cwd))
    subprocess.call(args, cwd=cwd)
    pass


def fix_image_files(root=os.curdir):
    for path, dirs, files in os.walk(os.path.abspath(root)):
        # sys.stdout.write('.')
        for dir in dirs:
            system_call("mogrify *.png", "{}".format(os.path.join(path, dir)))


fix_image_files(os.curdir)