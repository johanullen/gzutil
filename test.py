#!/usr/bin/env python

############################################################################
#                                                                          #
# Copyright (c) 2017 eBay Inc.                                             #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License");          #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#  http://www.apache.org/licenses/LICENSE-2.0                              #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
#                                                                          #
############################################################################

# Verify general operation and a few corner cases.

from __future__ import division, print_function, unicode_literals

from datetime import datetime, date, time
from sys import version_info
from itertools import compress
import gzutil

TMP_FN = "_tmp_test.gz"

inf, ninf = float("inf"), float("-inf")

if version_info[0] > 2:
	l = lambda i: i
else:
	l = long

# The Bits types don't accept floats, the others Int types do.
# This wasn't really intentional, but the right thing.

dttm0 = datetime(1789, 7, 14, 12, 42, 1, 82933)
dttm1 = datetime(2500, 12, 31, 23, 59, 59, 999999)
dttm2 = datetime(2015, 1, 1, 0, 0, 0, 0)
dt0 = date(1985, 7, 10)
tm0 = time(0, 0, 0, 0)
tm1 = time(2, 42, 0, 3)
tm2 = time(23, 59, 59, 999999)

for name, data, bad_cnt, res_data in (
	("Float64"       , ["0", float, 0   , 4.2, -0.01, 1e42, inf, ninf, None], 2, [0.0, 4.2, -0.01, 1e42, inf, ninf, None]),
	("Float32"       , ["0", float, l(0), 4.2, -0.01, 1e42, inf, ninf, None], 2, [0.0, 4.199999809265137, -0.009999999776482582, inf , inf, ninf, None]),
	("Int64"         , ["0", int, 0x8000000000000000, -0x8000000000000000, 0.1, 0x7fffffffffffffff, l(-5), None], 4, [0, 0x7fffffffffffffff, -5, None]),
	("Bits64"        , ["0", int, None, l(-5), -5, 0.1, 0x8000000000000000, 0x7fffffffffffffff, l(0x8000000000000000)], 6, [0x8000000000000000, 0x7fffffffffffffff, 0x8000000000000000]),
	("Int32"         , ["0", int, 0x80000000, -0x80000000, 0.1, 0x7fffffff, l(-5), None], 4, [0, 0x7fffffff, -5, None]),
	("Bits32"        , ["0", int, None, l(-5), -5, 0.1, 0x80000000, 0x7fffffff, l(0x80000000)], 6, [0x80000000, 0x7fffffff, 0x80000000]),
	("Number"        , ["0", int, 1 << 1007, -(1 << 1007), 1, l(0), -1, 0.5, 0x8000000000000000, -0x800000000000000, 1 << 340, (1 << 1007) - 1, -(1 << 1007) + 1, None], 4, [1, 0, -1, 0.5, 0x8000000000000000, -0x800000000000000, 1 << 340, (1 << 1007) - 1, -(1 << 1007) + 1, None]),
	("Bool"          , ["0", bool, 0.0, True, False, 0, l(1), None], 2, [False, True, False, False, True, None]),
	("BytesLines"    , [42, str, b"\n", u"a", b"a", b"foo bar baz", None], 4, [b"a", b"foo bar baz", None]),
	("AsciiLines"    , [42, str, b"\n", u"foo\xe4", b"foo\xe4", u"a", b"foo bar baz", None], 5, [str("a"), str("foo bar baz"), None]),
	("UnicodeLines"  , [42, str, u"\n", b"a", u"a", u"foo bar baz", None], 4, [u"a", u"foo bar baz", None]),
	("DateTime"      , [42, "now", tm0, dttm0, dttm1, dttm2, None], 3, [dttm0, dttm1, dttm2, None]),
	("Date"          , [42, "now", tm0, dttm0, dttm1, dttm2, dt0, None], 3, [dttm0.date(), dttm1.date(), dttm2.date(), dt0, None]),
	("Time"          , [42, "now", dttm0, tm0, tm1, tm2, None], 3, [tm0, tm1, tm2, None]),
	("ParsedFloat64" , [float, "1 thing", "", "0", " 4.2", -0.01, "1e42 ", " inf", "-inf ", None], 3, [0.0, 4.2, -0.01, 1e42, inf, ninf, None]),
	("ParsedFloat32" , [float, "1 thing", "", "0", " 4.2", -0.01, "1e42 ", " inf", "-inf ", None], 3, [0.0, 4.199999809265137, -0.009999999776482582, inf , inf, ninf, None]),
	("ParsedNumber"  , [int, "", str(1 << 1007), str(-(1 << 1007)), "0.0", 1, 0.0, "-1", "9223372036854775809", -0x800000000000000, str(1 << 340), str((1 << 1007) - 1), str(-(1 << 1007) + 1), None, "1e25"], 4, [0.0, 1, 0, -1, 0x8000000000000001, -0x800000000000000, 1 << 340, (1 << 1007) - 1, -(1 << 1007) + 1, None, 1e25]),
	("ParsedInt64"   , [int, "", "9223372036854775808", -0x8000000000000000, "0.1", 1, 0.1, "9223372036854775807", " -5 ", None], 5, [1, 0, 0x7fffffffffffffff, -5, None]),
	("ParsedBits64"  , [int, "", None, l(-5), "-5", 0.1, " 9223372036854775808", "9223372036854775807 ", "0", 1], 5, [0, 0x8000000000000000, 0x7fffffffffffffff, 0, 1]),
	("ParsedInt32"   , [int, "", 0x80000000, -0x80000000, "0.1", 0.1, "-7", "-0", "2147483647", " -5 ", None, 1], 5, [0, -7, 0, 0x7fffffff, -5, None, 1]),
	("ParsedBits32"  , [int, "", None, l(-5), -5, 0.1, "2147483648", "2147483647", l(0x80000000), 1], 5, [0, 0x80000000, 0x7fffffff, 0x80000000, 1]),
):
	print(name)
	r_name = "Gz" + name[6:] if name.startswith("Parsed") else "Gz" + name
	r_typ = getattr(gzutil, r_name)
	w_typ = getattr(gzutil, "GzWrite" + name)
	# verify that failuses in init are handled reasonably.
	for typ in (r_typ, w_typ,):
		try:
			typ("/NONEXISTENT")
			raise Exception("%r does not give IOError for /NONEXISTENT" % (typ,))
		except IOError:
			pass
		try:
			typ("/NONEXISTENT", nonexistent_keyword="test")
			raise Exception("%r does not give TypeError for bad keyword argument" % (typ,))
		except TypeError:
			pass
	# test that the right data fails to write
	with w_typ(TMP_FN) as fh:
		count = 0
		for ix, value in enumerate(data):
			try:
				fh.write(value)
				count += 1
				assert ix >= bad_cnt, repr(value)
			except (ValueError, TypeError, OverflowError):
				assert ix < bad_cnt, repr(value)
		assert fh.count == count, "%s: %d lines written, claims %d" % (name, count, fh.count,)
		if "Lines" not in name:
			want_min = min(filter(lambda x: x is not None, res_data))
			want_max = max(filter(lambda x: x is not None, res_data))
			assert fh.min == want_min, "%s: claims min %r, not %r" % (name, fh.min, want_min,)
			assert fh.max == want_max, "%s: claims max %r, not %r" % (name, fh.max, want_max,)
	# Okay, errors look good
	with r_typ(TMP_FN) as fh:
		res = list(fh)
		assert res == res_data, res
	# Data comes back as expected.
	if name.endswith("Lines"):
		continue # no default support
	for ix, default in enumerate(data):
		# Verify that defaults are accepted where expected
		try:
			with w_typ(TMP_FN, default=default) as fh:
				pass
			assert ix >= bad_cnt, repr(default)
		except AssertionError:
			raise
		except Exception:
			assert ix < bad_cnt, repr(default)
		if ix >= bad_cnt:
			with w_typ(TMP_FN, default=default) as fh:
				count = 0
				for value in data:
					try:
						fh.write(value)
						count += 1
					except (ValueError, TypeError, OverflowError):
						assert 0, "No default: %r" % (value,)
				assert fh.count == count, "%s: %d lines written, claims %d" % (name, count, fh.count,)
			# No errors when there is a default
			with r_typ(TMP_FN) as fh:
				res = list(fh)
				assert res == [res_data[ix - bad_cnt]] * bad_cnt + res_data, res
			# Great, all default values came out right in the file!
	# Verify hashing and slicing
	def slice_test(slices, spread_None):
		res = []
		sliced_res = []
		total_count = 0
		for sliceno in range(slices):
			with w_typ(TMP_FN, hashfilter=(sliceno, slices, spread_None)) as fh:
				count = 0
				for ix, value in enumerate(data):
					try:
						wrote = fh.write(value)
						count += wrote
						assert ix >= bad_cnt, repr(value)
						assert fh.hashcheck(value) == wrote or (spread_None and value is None), "Hashcheck disagrees with write"
					except (ValueError, TypeError, OverflowError):
						assert ix < bad_cnt, repr(value)
				assert fh.count == count, "%s (%d, %d): %d lines written, claims %d" % (name, sliceno, slices, count, fh.count,)
				if "Lines" not in name:
					got_min, got_max = fh.min, fh.max
			total_count += count
			with r_typ(TMP_FN) as fh:
				tmp = list(fh)
			assert len(tmp) == count, "%s (%d, %d): %d lines written, claims %d" % (name, sliceno, slices, len(tmp), count,)
			for v in tmp:
				assert (spread_None and v is None) or w_typ.hash(v) % slices == sliceno, "Bad hash for %r" % (v,)
				if "Bits" not in name or v < 0x8000000000000000:
					assert w_typ.hash(v) == gzutil.hash(v), "Inconsistent hash for %r" % (v,)
			res.extend(tmp)
			sliced_res.append(tmp)
			if "Lines" not in name:
				tmp = list(filter(lambda x: x is not None, tmp))
				if tmp:
					want_min = min(tmp)
					want_max = max(tmp)
					assert got_min == want_min, "%s (%d, %d): claims min %r, not %r" % (name, sliceno, slices, got_min, want_min,)
					assert got_max == want_max, "%s (%d, %d): claims max %r, not %r" % (name, sliceno, slices, got_max, want_max,)
				else:
					assert got_min is None and got_max is None
		assert len(res) == total_count, "%s (%d): %d lines written, claims %d" % (name, slices, len(res), total_count,)
		assert len(res) == len(res_data), "%s (%d): %d lines written, should be %d" % (name, slices, len(res), len(res_data),)
		assert set(res) == set(res_data), "%s (%d): Wrong data: %r != %r" % (name, slices, res, res_data,)
		# verify reading back with hashfilter gives the same as writing with it
		with w_typ(TMP_FN) as fh:
			for value in data[bad_cnt:]:
				fh.write(value)
		for sliceno in range(slices):
			with r_typ(TMP_FN, hashfilter=(sliceno, slices, spread_None)) as fh:
				slice_values = list(compress(res_data, fh))
			assert slice_values == sliced_res[sliceno], "Bad reader hashfilter: slice %d of %d gave %r instead of %r" % (sliceno, slices, slice_values, sliced_res[sliceno],)
	for slices in range(1, 24):
		slice_test(slices, False)
		slice_test(slices, True)
		# and a simple check to verify that None actually gets spread too
		if "Bits" not in name:
			with w_typ(TMP_FN, hashfilter=(slices - 1, slices, True)) as fh:
				for _ in range(slices * 3):
					fh.write(None)
			with r_typ(TMP_FN) as fh:
				tmp = list(fh)
				assert tmp == [None, None, None], "Bad spread_None for %d slices" % (slices,)

print("Hash testing, false things")
for v in (None, "", b"", 0, 0.0, False,):
	assert gzutil.hash(v) == 0, "%r doesn't hash to 0" % (v,)
print("Hash testing, strings")
for v in ("", "a", "0", "foo", "a slightly longer string", "\0", "a\0b",):
	u = gzutil.GzWriteUnicodeLines.hash(v)
	a = gzutil.GzWriteAsciiLines.hash(v)
	b = gzutil.GzWriteBytesLines.hash(v.encode("utf-8"))
	assert u == a == b, "%r doesn't hash the same" % (v,)
assert gzutil.hash(b"\xe4") != gzutil.hash("\xe4"), "Unicode hash fail"
assert gzutil.GzWriteBytesLines.hash(b"\xe4") != gzutil.GzWriteUnicodeLines.hash("\xe4"), "Unicode hash fail"
try:
	gzutil.GzWriteAsciiLines.hash(b"\xe4")
	raise Exception("Ascii.hash acceptet non-ascii")
except ValueError:
	pass
print("Hash testing, numbers")
for v in (0, 1, 2, 9007199254740991, -42):
	assert gzutil.GzWriteInt64.hash(v) == gzutil.GzWriteFloat64.hash(float(v)), "%d doesn't hash the same" % (v,)
	assert gzutil.GzWriteInt64.hash(v) == gzutil.GzWriteNumber.hash(v), "%d doesn't hash the same" % (v,)

print("BOM test")
def test_read_bom(num, prefix=""):
	with gzutil.GzBytesLines(TMP_FN) as fh:
		data = list(fh)
		assert data == [prefix.encode("utf-8") + b"\xef\xbb\xbfa", b"\xef\xbb\xbfb"], (num, data)
	with gzutil.GzBytesLines(TMP_FN, strip_bom=True) as fh:
		data = list(fh)
		assert data == [prefix.encode("utf-8") + b"a", b"\xef\xbb\xbfb"], (num, data)
	with gzutil.GzUnicodeLines(TMP_FN) as fh:
		data = list(fh)
		assert data == [prefix + "\ufeffa", "\ufeffb"], (num, data)
	with gzutil.GzUnicodeLines(TMP_FN, strip_bom=True) as fh:
		data = list(fh)
		assert data == [prefix + "a", "\ufeffb"], (num, data)
	with gzutil.GzUnicodeLines(TMP_FN, "latin-1") as fh:
		data = list(fh)
		assert data == [prefix.encode("utf-8").decode("latin-1") + u"\xef\xbb\xbfa", u"\xef\xbb\xbfb"], (num, data)
	with gzutil.GzUnicodeLines(TMP_FN, "latin-1", strip_bom=True) as fh:
		data = list(fh)
		assert data == [prefix.encode("utf-8").decode("latin-1") + u"a", u"\xef\xbb\xbfb"], (num, data)
	with gzutil.GzUnicodeLines(TMP_FN, "ascii", "ignore") as fh:
		data = list(fh)
		assert data == ["a", "b"], (num, data)
	if version_info[0] > 2:
		with gzutil.GzAsciiLines(TMP_FN) as fh:
			try:
				next(fh)
				raise Exception("GzAsciiLines allowed non-ascii in python3")
			except ValueError:
				pass

with open(TMP_FN, "wb") as fh:
	fh.write(b"\xef\xbb\xbfa\n\xef\xbb\xbfb")
test_read_bom(0)
with gzutil.GzWriteUnicodeLines(TMP_FN, write_bom=True) as fh:
	fh.write("a")
	fh.write("\ufeffb")
test_read_bom(1)
with gzutil.GzWriteUnicodeLines(TMP_FN, write_bom=True) as fh:
	fh.write("\ufeffa")
	fh.write("\ufeffb")
test_read_bom(2, "\ufeff")
with gzutil.GzWriteUnicodeLines(TMP_FN) as fh:
	fh.write("a")
assert next(gzutil.GzBytesLines(TMP_FN)) == b"a", "GzWriteUnicodeLines writes BOM when not requested"

print("Append test")
# And finally verify appending works as expected.
with gzutil.GzWriteInt64(TMP_FN) as fh:
	fh.write(42)
with gzutil.GzWriteInt64(TMP_FN, mode="a") as fh:
	fh.write(18)
with gzutil.GzInt64(TMP_FN) as fh:
	assert list(fh) == [42, 18]

print("Untyped writer test")
with gzutil.GzWrite(TMP_FN) as fh:
	class SubString(bytes): pass
	for v in (b"apa", "beta", 42, None, SubString(b"\n"), b"foo"):
		try:
			fh.write(v)
			assert isinstance(v, bytes), "GzWrite accepted %r" % (type(v),)
		except ValueError:
			assert not isinstance(v, bytes), "GzWrite doesn't accept %r" % (type(v),)
			pass
with gzutil.GzAsciiLines(TMP_FN) as fh:
	res = list(fh)
	assert res == ["apa", "foo"], "Failed to read back GzWrite written stuff: %r" % (res,)

print("Line boundary test")
Z = 128 * 1024 # the internal buffer size in gzutil
a = [
	"x" * (Z - 2) + "a",         # \n at end of buffer
	"X" * (Z - 1) + "A",         # \n at start of 2nd buffer
	"y" * (Z - 4) + "b",         # leave one char in 1st buffer
	"Y" * (Z * 2 - 1) + "B",     # \n at start of 3rd buffer
	"12345" * Z + "z" * (Z - 1), # \n at end of 6th buffer
	"Z",
]
with gzutil.GzWriteAsciiLines(TMP_FN) as fh:
	for v in a:
		fh.write(v)
with gzutil.GzAsciiLines(TMP_FN) as fh:
	b = list(fh)
assert a == b, b

print("Number boundary test")
with gzutil.GzWriteNumber(TMP_FN) as fh:
	todo = Z - 100
	while todo > 0:
		fh.write(42)
		todo -= 9
	# v goes over a block boundary.
	v = 0x2e6465726f6220657261206577202c6567617373656d20676e6f6c207974746572702061207369207374696220646e6173756f6874206120796c6c6175746341203f7468676972202c6c6c657720736120746867696d206577202c65726568206567617373656d2074726f68732061206576616820732774656c20796548
	want = [42] * fh.count + [v]
	fh.write(v)
with gzutil.GzNumber(TMP_FN) as fh:
	assert want == list(fh)

print("Number max_count large end test")
with gzutil.GzWriteNumber(TMP_FN) as fh:
	fh.write(2 ** 1000)
	fh.write(7)
with gzutil.GzNumber(TMP_FN, max_count=1) as fh:
	assert [2 ** 1000] == list(fh)

print("Callback tests")
with gzutil.GzWriteNumber(TMP_FN) as fh:
	for n in range(1000):
		fh.write(n)
def callback(num_lines):
	global cb_count
	cb_count += 1
	if cb_interval > 1:
		assert num_lines in good_num_lines or num_lines == 1000 + cb_offset
for cb_interval, max_count, expected_cb_count in (
	(300, -1, (3,)),
	(250, 300, (1,)),
	(250, 200, (0,)),
	(1, -1, (999, 1000,)),
	(5, -1, (199, 200,)),
	(5, 12, (2,)),
	(10000, -1, (0,)),
):
	for cb_offset in (0, 50000000, -10000):
		cb_count = 0
		good_num_lines = range(cb_interval + cb_offset, (1000 if max_count == -1 else max_count) + cb_offset, cb_interval)
		with gzutil.GzNumber(TMP_FN, max_count=max_count, callback=callback, callback_interval=cb_interval, callback_offset=cb_offset) as fh:
			lst = list(fh)
			assert len(lst) == 1000 if max_count == -1 else max_count
		assert cb_count in expected_cb_count
def callback2(num_lines):
	raise StopIteration
with gzutil.GzNumber(TMP_FN, callback=callback2, callback_interval=1) as fh:
	lst = list(fh)
	assert lst == [0]
def callback3(num_lines):
	1 / 0
with gzutil.GzNumber(TMP_FN, callback=callback3, callback_interval=1) as fh:
	good = False
	try:
		lst = list(fh)
	except ZeroDivisionError:
		good = True
	assert good
