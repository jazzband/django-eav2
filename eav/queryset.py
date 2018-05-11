#!/usr/bin/env python
#
#    This software is derived from EAV-Django originally written and
#    copyrighted by Andrey Mikhaylenko <http://pypi.python.org/pypi/eav-django>
#
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This software is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with EAV-Django.  If not, see <http://gnu.org/licenses/>.

from django.db.models.query import QuerySet

from .decorators import eav_filter


class EavQuerySet(QuerySet):
    @eav_filter
    def filter(self, *args, **kwargs):
        '''
        Pass *args* and *kwargs* through :func:`eav_filter`, then pass to
        the ``models.Manager`` filter method.
        '''
        return super().filter(*args, **kwargs).distinct()

    @eav_filter
    def exclude(self, *args, **kwargs):
        '''
        Pass *args* and *kwargs* through :func:`eav_filter`, then pass to
        the ``models.Manager`` exclude method.
        '''
        return super().exclude(*args, **kwargs).distinct()

    @eav_filter
    def get(self, *args, **kwargs):
        '''
        Pass *args* and *kwargs* through :func:`eav_filter`, then pass to
        the ``models.Manager`` get method.
        '''
        return super().get(*args, **kwargs)
