"""
Allows you to set and manage individual appearance features for an object.

Can be used for character features, like hair, limbs, etc. or for object features like material, size, etc.

Currently largely undocumented, sorry!
"""

import inflect
from evennia.utils import list_to_string, logger

_INFLECT = inflect.engine()

_FEATURE_ATTR = "feature_dict"
_FEATURE_CAT = "system"

class FeatureError(RuntimeError):
	"""
	Appearance or feature error.
	"""

class FeatureHandler():
	"""
	Saves and returns an object's feature-based appearance.
	"""

	def __init__(self, obj, feature_attr=_FEATURE_ATTR):
		"""
		Initialize the handler.
		"""
		self.obj = obj

		self.features = obj.attributes.get(feature_attr, category=_FEATURE_CAT)
		if not self.features:
			obj.attributes.add(feature_attr, {}, category=_FEATURE_CAT)
			self.features = obj.attributes.get(feature_attr, category=_FEATURE_CAT)

	@property
	def all(self):
		return self.features.keys()

	@property
	def view(self):
		feature_list = []
		# parse the features here
		for feature in self.features:
			feature_list.append(self.get(feature))
		
		return list_to_string(feature_list)

	def options(self, name):
		"""
		View the possible attributes for different features
		"""
		# feature doesn't exist
		if name not in self.features:
			return None
		
		# feature doesn't have any options
		if not self.features[name]['format']:
			return None
		
		# feature has options, get them
		else:
			feature = dict(self.features[name])
			feature.pop('format',None)
			feature.pop('article',None)
			feature.pop('prefix',None)
			return(list(feature.keys()))
		
	def get(self, name, as_dict=False):
		"""
		Returns a formatted string for the feature.
		"""
		if name == "all":
			return dict(self.features) if as_dict else self.view

		if name not in self.features:
			return None

		feature = dict(self.features[name])
		if as_dict:
			# return the dict as-is
			return { key: value for key, value in feature.items() if not key.startswith("_") }

		else:
			# get the appearance of just one feature
			article = feature.pop('article',False)
			if feature.get('format',None):
				# format with key values
				string = feature.pop('format')
				stringable = { key: list_to_string(value) if type(value) is not str else value for key, value in feature.items() }
				string = string.format(**stringable)
			else:
				string = feature.pop('value',None)
				string = list_to_string(string) if type(string) is list else string
			string = f"{feature['prefix']} {string}" if feature['prefix'] else string
			# add an article if the feature specifies to do so
			string = _INFLECT.an(string) if article else string
			# compress whitespace
			string = " ".join(string.strip().split())
			# add feature
			string = f"{string} {name}" if string else name
			
			return string

	def set(self, name, soft=False, **kwargs):
		"""
		Sets specific values or options
		"""
		if name not in self.features:
			raise FeatureError(f"Feature \"{name}\" does not exist on this object, use .add instead.")
		
		for key, value in kwargs.items():
			default_key = f"_default_{key}"
			if soft:
				# save "real" values before doing soft assignment
				if default_key not in self.features[name]:
					self.features[name][default_key] = self.features[name][key]
			self.features[name][key] = value

	def merge(self, name, soft=False, **kwargs):
		"""
		Merges additional values into feature options, or adds a new
		feature if it doesn't exist.
		"""
		if name not in self.features:
			self.add(name, **kwargs)
			return

		nothing = [ kwargs.pop(key) for key in ["format", "article", "prefix"] ]

		for key, value in kwargs.items():
			if key in self.features[name]:
				current = self.features[name][key]
				default_key = f"_default_{key}"
				if soft:
					# save "real" values before doing soft merge
					if default_key not in self.features[name]:
						self.features[name][default_key] = current
				# reset back to "real" values before hard merge
				elif default_key in self.features[name]:
					self.reset(name)

				if type(current) is not str:
					if value not in current:
						self.features[name][key].append(value)
				elif value != current:
					self.features[name][key] = [self.features[name][key], value]
			else:
				self.features[name][key] = value

	def add(self, name, value=None, format=None, force=False, prefix=None, article=False, **kwargs):
		if not force and name in self.features:
			raise FeatureError(f"Feature \"{name}\" already exists and would be overwritten.")
		feature = { "format": format, "article": article, "prefix": prefix }
		# if format is set, grab values from kwargs
		if format and type(format) is str:
			for key, value in kwargs.items():
				feature[key] = value
		elif value:
			feature['value'] = value
		else:
			raise FeatureError("No valid values provided when adding a feature.")

		# overwrite any existing feature of this name
		self.features[name] = feature
	
	def remove(self, feature):
		self.features.pop(feature, None)
	
	def reset(self):
		for feature, feature_dict in self.features:
			for key, value in feature_dict.items():
				default_key = f"_default_{key}"
				if default_key in feature_dict:
					feature_dict[key] = feature_dict.pop(default_key)

	def clear(self):
		key_list = list(self.features.keys())
		for key in key_list:
			self.features.pop(key)
