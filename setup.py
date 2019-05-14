from subprocess import check_call
import sys
from setuptools import setup

if sys.argv[-1] in ('build', 'publish'):
    check_call(
        'rst_include include -s ./_README.rst -t ./README.rst', shell=True)
    check_call('python setup.py sdist bdist_wheel', shell=True)
    if sys.argv[-1] == 'publish':
        check_call('twine check dist/*', shell=True)
        check_call('twine upload dist/*', shell=True)
    sys.exit()


def main():

    setup(
        name = 'polydatum',
        packages=['polydatum'],
        package_dir = {'':'src'},
        version = open('VERSION.txt').read().strip(),
        author='Mike Thornton',
        author_email='six8@devdetails.com',
        url='https://github.com/plynth/polydatum',
        keywords=['orm', 'persistence'],
        license='MIT',
        description='An encapsulated persistance layer for Python',
        classifiers = [
            "Programming Language :: Python",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Natural Language :: English",
            "Topic :: Software Development :: Libraries :: Python Modules",
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',            
        ],
        long_description=open('README.rst').read(),
        long_description_content_type='text/x-rst',
        install_requires = [
            'six==1.12.0',
            'werkzeug',
        ],
    )

if __name__ == '__main__':
    main()