#!/usr/bin/python
#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path

import portage.exception as pe
from portage.versions import catsplit

from gentoopm.basepm.repo import PMRepositoryDict, PMEbuildRepository, \
		PMRepository
from gentoopm.portagepm.atom import PortageAtom, CompletePortageAtom
from gentoopm.portagepm.pkg import PortageCPV, PortageDBCPV, PortagePackageSet, \
		PortageFilteredPackageSet
from gentoopm.util import StringWrapper

class PortageRepoDict(PMRepositoryDict):
	def __iter__(self):
		for p_repo in self._dbapi.repositories:
			yield PortageRepository(p_repo, self._dbapi)

	def __getitem__(self, key):
		key = str(key)
		try:
			if os.path.isabs(key):
				repo_name = self._dbapi.repositories.get_name_for_location(key)
			else:
				repo_name = key
			r = self._dbapi.repositories[repo_name]
		except KeyError:
			raise KeyError('No repository matched key %s' % key)
		else:
			return PortageRepository(r, self._dbapi)

	def __init__(self, portdbapi):
		self._dbapi = portdbapi

class PortageFilteredDBRepo(PortageFilteredPackageSet):
	def __init__(self, repo, atom):
		self._dbapi = repo._dbapi
		self._atom = atom._atom

	@property
	def _stringified_atom(self):
		a = str(self._atom)
		return a.replace('null/', '')

	def __iter__(self):
		a = self._stringified_atom
		try:
			it = self._dbapi.match(a)
		except pe.AmbiguousPackageName as e:
			for pkgcand in e.args[0]:
				for p in PortageHackedFilteredDBRepo(self, pkgcand):
					yield p
		else:
			for p in it:
				yield PortageDBCPV(p, self._dbapi)

class PortageHackedFilteredDBRepo(PortageFilteredDBRepo):
	def __init__(self, repo, pkgcand):
		cat = catsplit(pkgcand)[0]
		self._atom = str(repo._atom).replace('null/', '%s/' % cat)
		self._dbapi = repo._dbapi

	@property
	def _stringified_atom(self):
		return self._atom

class PortDBRepository(PortagePackageSet, PMRepository):
	def __init__(self, dbapi):
		self._dbapi = dbapi

	def __iter__(self):
		for p in self._dbapi.cpv_all(): # XXX
			yield PortageDBCPV(p, self._dbapi)

	_filtered_subclass = PortageFilteredDBRepo
	def filter(self, *args, **kwargs):
		newargs = []
		filt = None
		for a in args:
			if isinstance(a, str):
				a = PortageAtom(a)
			if isinstance(a, CompletePortageAtom) and filt is None:
				filt = a
			else:
				newargs.append(a)

		pset = self
		if filt:
			pset = self._filtered_subclass(pset, filt)
		if newargs or kwargs:
			pset = PortageFilteredPackageSet(pset, newargs, kwargs)
		return pset

class PortageFilteredRepo(PortageFilteredDBRepo):
	def __init__(self, repo, atom):
		PortageFilteredDBRepo.__init__(self, repo, atom)
		self._name = repo.name
		self._path = str(repo.path)
		self._prio = repo._repo.priority

	def __iter__(self):
		if self._atom.repo is not None:
			if self._atom.repo != self._name:
				return
			a = self._stringified_atom
		else:
			a = '%s::%s' % (self._stringified_atom, self._name)

		try:
			it = self._dbapi.xmatch("match-all", a)
		except pe.AmbiguousPackageName as e:
			for pkgcand in e.args[0]:
				for p in PortageHackedFilteredRepo(self, pkgcand):
					yield p
		else:
			for p in it:
				yield PortageCPV(p, self._dbapi, self._path, self._prio)

class PortageHackedAtom(object):
	def __init__(self, s, repo):
		self._s = s
		self._repo = repo

	@property
	def repo(self):
		return self._repo

	def __str__(self):
		return self._s

class PortageHackedFilteredRepo(PortageFilteredRepo):
	def __init__(self, repo, pkgcand):
		cat = catsplit(pkgcand)[0]
		self._atom = PortageHackedAtom(
				str(repo._atom).replace('null/', '%s/' % cat),
				repo._atom.repo)
		self._dbapi = repo._dbapi
		self._path = repo._path
		self._prio = repo._prio
		self._name = repo._name

	@property
	def _stringified_atom(self):
		return str(self._atom)

class PortageRepository(PortDBRepository, PMEbuildRepository):
	def __init__(self, repo_obj, portdbapi):
		self._repo = repo_obj
		PortDBRepository.__init__(self, portdbapi)

	def __iter__(self):
		path = str(self.path)
		prio = self._repo.priority
		for cp in self._dbapi.cp_all(trees = (path,)):
			for p in self._dbapi.cp_list(cp, mytree = path):
				yield PortageCPV(p, self._dbapi, path, prio)

	_filtered_subclass = PortageFilteredRepo

	@property
	def name(self):
		return StringWrapper(self._repo.name)

	@property
	def path(self):
		return StringWrapper(self._repo.location)

	def __lt__(self, other):
		return self._repo.priority < other._repo.priority

class VDBRepository(PortDBRepository):
	pass
