#!/usr/bin/python
#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path
from abc import abstractmethod, abstractproperty

from gentoopm.util import ABCObject

class PMRepositoryDict(ABCObject):
	"""
	A dict-like object providing access to a set of repositories.

	The repositories can be referenced through their names or paths,
	or iterated over. An access should result in an instantiated PMRepository
	subclass.
	"""

	def __getitem__(self, key):
		"""
		Get the repository by its name or path. If using a path as a key,
		an absolute path must be passed.

		By default, iterates over the repository list. Can be replaced with
		something more optimal.
		"""
		bypath = os.path.isabs(key)

		for r in self:
			if bypath:
				# We're requiring exact match to match portage behaviour
				m = r.path == key
			else:
				m = r.name == key
			if m:
				return r
		raise KeyError('No repository matched key %s' % key)

	@abstractmethod
	def __iter__(self):
		"""
		Iterate over the repository list.
		"""
		pass

class PackageManager(ABCObject):
	"""
	Base abstract class for a package manager.
	"""

	@abstractproperty
	def name(self):
		"""
		Return the canonical name of the PM. The value should be static
		and unique.
		"""
		pass

	@abstractmethod
	def reload_config(self):
		"""
		(Re-)load the configuration of a particular package manager. Set up
		internal variables.

		Called by default __init__().
		"""
		pass

	def __init__(self):
		self.reload_config()

	@abstractproperty
	def repositories(self):
		"""
		Return an PMRepositoryDict subclass referring to the currently enabled
		ebuild repositories.
		"""
		pass
