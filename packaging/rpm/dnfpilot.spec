Name:           dnfpilot
Version:        0.1.0
Release:        1%{?dist}
Summary:        Update Fedora with dnf and Flatpak, without Discover's offline update
License:        MIT
URL:            https://github.com/TechnikWeber/DnfPilot
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
Requires:       python3-pyside6
Requires:       polkit
Requires:       dnf5
Recommends:     flatpak
Recommends:     PackageKit

%description
A small window that runs dnf upgrade --refresh and flatpak update with a
progress bar, fold-out details and a restart button, plus a Repair menu for
when Discover's offline update keeps failing.

%prep
%autosetup

%build
# pure Python, nothing to build

%install
install -d %{buildroot}%{python3_sitelib}/dnfpilot
install -m644 dnfpilot/*.py dnfpilot/helper.sh dnfpilot/dnfpilot.svg \
    %{buildroot}%{python3_sitelib}/dnfpilot/
install -Dm755 /dev/stdin %{buildroot}%{_bindir}/dnfpilot <<'SH'
#!/usr/bin/python3 -s
from dnfpilot.app import main
raise SystemExit(main())
SH
desktop-file-install --dir=%{buildroot}%{_datadir}/applications share/dnfpilot.desktop
install -Dm644 dnfpilot/dnfpilot.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/dnfpilot.svg
install -Dm644 share/io.github.technikweber.dnfpilot.metainfo.xml \
    %{buildroot}%{_metainfodir}/io.github.technikweber.dnfpilot.metainfo.xml

%check
%{python3} -m unittest discover -s tests -t .

%files
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/dnfpilot
%{python3_sitelib}/dnfpilot/
%{_datadir}/applications/dnfpilot.desktop
%{_datadir}/icons/hicolor/scalable/apps/dnfpilot.svg
%{_metainfodir}/io.github.technikweber.dnfpilot.metainfo.xml

%changelog
* Wed Nov 11 2026 Philipp Weber - 0.1.0-1
- First release
