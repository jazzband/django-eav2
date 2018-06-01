from distutils.core import setup

setup(
    name='django-eav',
    version=__import__('eav').__version__,
    license = 'GNU Lesser General Public License (LGPL), Version 3',

    requires = ['python (>= 2.5)', 'django (>= 1.2)'],
    provides = ['eav'],

    description='Entity-attribute-value model implementation as a reusable'
                'Django app.',
    long_description=open('README.md').read(),

    url='http://github.com/mvpdev/django-eav',

    packages=['eav', 'tests'],

    classifiers  = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
