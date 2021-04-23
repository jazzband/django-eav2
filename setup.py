from setuptools import setup, find_packages

setup(
    name             = 'django-eav2',
    version          = __import__('eav').__version__,
    license          = 'GNU Lesser General Public License (LGPL), Version 3',
    requires         = ['python (>= 3.6)', 'django (>= 3.1)'],
    provides         = ['eav'],
    description      = 'Entity-Attribute-Value storage for Django',
    url              = 'http://github.com/lvm/django-eav2',
    packages         = find_packages(),
    maintainer       = 'Mauro Lizaur',
    maintainer_email = 'mauro@sdf.org',

    classifiers  = [
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
