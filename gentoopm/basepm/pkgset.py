#!/usr/bin/python
#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from abc import abstractmethod

from gentoopm.exceptions import EmptyPackageSetError, AmbiguousPackageSetError
from gentoopm.util import ABCObject, BoolCompat

class PMPackageSet(ABCObject, BoolCompat):
	""" A set of packages. """

	@abstractmethod
	def __iter__(self):
		"""
		Iterate over the packages (or sets) in a set.

		@return: packages in the set
		@rtype: iter(L{PMPackage})
		"""
		pass

	def filter(self, *args, **kwargs):
		"""
		Filter the packages based on arguments. Return a filtered package set.

		The positional arguments can provide a number of L{PMPackageMatcher}s
		and/or a L{PMAtom} instance. The keyword arguments match metadata keys
		using '==' comparison with passed string (or L{PMKeywordMatcher}s).

		Multiple filters will be AND-ed together. Same applies for .filter()
		called multiple times. You should, however, avoid passing multiple
		atoms as it is not supported by all PMs.

		@param args: list of package matchers
		@type args: list(L{PMPackageMatcher},L{PMAtom})
		@param kwargs: dict of keyword matchers
		@type kwargs: dict(string -> L{PMKeywordMatcher})
		@return: filtered package set
		@rtype: L{PMFilteredPackageSet}
		@raise KeyError: when invalid metadata key is referenced in kwargs
		"""

		return PMFilteredPackageSet(self, args, kwargs)

	@property
	def best(self):
		"""
		Return the best-matching package in the set (the newest one).

		@type: L{PMPackage}
		@raise EmptyPackageSetError: when no packages match the condition
		@raise AmbiguousPackageSetError: when packages with different keys
			match the condition
		"""

		best = None
		for p in self.sorted:
			if best is not None and p.key != best.key:
				raise AmbiguousPackageSetError('.best called on a set of differently-named packages')
			best = p

		if best is None:
			raise EmptyPackageSetError('.best called on an empty set')

		return best

	def select(self, *args, **kwargs):
		"""
		Select a single package matching keys in positional and keyword
		arguments. This is a convenience wrapper for C{filter(*args,
		**kwargs).best}.

		@param args: list of package matchers
		@type args: list(L{PMPackageMatcher},L{PMAtom})
		@param kwargs: dict of keyword matchers
		@type kwargs: dict(string -> L{PMKeywordMatcher})
		@return: filtered package set
		@rtype: L{PMFilteredPackageSet}
		@raise KeyError: when invalid metadata key is referenced in kwargs
		@raise EmptyPackageSetError: when no packages match the condition
		@raise AmbiguousPackageSetError: when packages with different keys
			match the condition
		"""
		try:
			return self.filter(*args, **kwargs).best
		except EmptyPackageSetError:
			raise EmptyPackageSetError('No packages match the filters.')
		except AmbiguousPackageSetError:
			raise AmbiguousPackageSetError('Ambiguous filter (matches more than a single package name).')

	@property
	def sorted(self):
		"""
		Return a sorted variant of the package set. The packages will be sorted
		in a standard PM manner, with better packages coming later. The key
		ordering is undefined, although usually they will come sorted
		lexically.

		@return: sorted package set
		@rtype: L{PMSortedPackageSet}
		"""
		return PMSortedPackageSet(self)

	def __getitem__(self, filt):
		"""
		Select a single package matching an atom (or filter). Unlike L{select()},
		this one doesn't choose the best match but requires the filter to match
		exactly one package.

		@param filt: a package matcher or an atom
		@type filt: L{PMPackageMatcher}/L{PMAtom}
		@return: matching package
		@rtype: L{PMPackage}
		@raise EmptyPackageSetError: when no packages match the condition
		@raise AmbiguousPackageSetError: when packages with different keys
			match the condition
		"""

		it = iter(self.filter(filt))

		try:
			ret = next(it)
		except StopIteration:
			raise EmptyPackageSetError('No packages match the filter.')
		try:
			next(it)
		except StopIteration:
			pass
		else:
			raise AmbiguousPackageSetError('Filter matches more than one package.')

		return ret

	def __contains__(self, arg):
		"""
		Check whether the package set contains at least a single package
		matching the filter or package atom passed as an argument.

		@param arg: a package matcher or an atom
		@type arg: L{PMPackageMatcher}/L{PMAtom}
		@return: True if at least a single package matched
		@rtype: bool
		"""

		i = iter(self.filter(arg))
		try:
			next(i)
		except StopIteration:
			return False
		return True

	def __bool__(self):
		"""
		Check whether the package set is non-empty.

		@return: True if package set matches at least one package.
		@rtype: bool
		"""
		try:
			next(iter(self))
		except StopIteration:
			return False
		return True

class PMFilteredPackageSet(PMPackageSet):
	def __init__(self, src, args, kwargs):
		self._src = src
		self._args = args
		self._kwargs = kwargs

	def __iter__(self):
		for el in self._src:
			if el._matches(*self._args, **self._kwargs):
				yield el

class PMSortedPackageSet(PMPackageSet):
	def __init__(self, src):
		self._src = src

	def __iter__(self):
		return iter(sorted(self._src))
