# Notices and attribution

xkoranate-ce-python is a Python/PySide6 rewrite of **xkoranate-CE**, originally
written in Qt4/C++ by **Commerce Heights (ThirdGeek)** <thirdgeek@gmail.com>,
released 2008–2011. Original source: <https://github.com/NS-Sports/Xkoranate-CE>.

The whole program (this rewrite included) is licensed under the GNU General
Public License v3.0 or later — see [LICENSE](LICENSE).

## Python port maintainers

The Python/PySide6 rewrite is developed and actively maintained by:

- **Mertagne**
- **Osarius**

## Original contributors

- Code based upon **NSFootySim** 2.0.7.2 and 3.0.1, © 2004–2010 Vephrall and
  Dancougar, released under the GNU General Public License.
  <http://ten93.com/nsfs/nsfs3.html>
- Code based upon **Footba11er** 1.03, **Golfinator** 1.00, and **Howzzat** 1a
  by The Babbage Islands, incorporated with permission.
- Code based upon **Liventia's auto racing scorinator**, incorporated with
  permission.
- Sport files contributed by The Babbage Islands, Kelssek, and Liventia.

## Third-party components (current Python port)

- **PySide6** (Qt for Python), © The Qt Company, licensed under the LGPLv3.
  Used as an unmodified dependency, not vendored — see
  <https://www.qt.io/licensing/> and the LGPLv3 text at
  <https://www.gnu.org/licenses/lgpl-3.0.html>.
- **QtAwesome**, used for in-app icons, bundles the Material Design Icons,
  Remix Icon, Elusive Icons, and Codicons font sets under their respective
  licenses (SIL OFL / MIT / CC). Used as an unmodified dependency, not
  vendored — see <https://github.com/spyder-ide/qtawesome>.

(The original C++ program bundled portions of Qt 4.7.3 and the KDE Oxygen
icon theme directly; the Python port instead depends on PySide6 and
QtAwesome as ordinary packages, so their license texts are not reproduced
here.)
