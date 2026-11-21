# 🌊 MacWave Data

The package index that MacWave reads at runtime: where every package and
dependency comes from, its `sha256`, and what it depends on.

> **Note**: this data used to live on the `infosource` branch of
> `MacWaveOrg/MacWave`. Since 3.0 it lives here, on `main`.

# 🌊 Official Website

[macwave.org](https://macwave.org)

# 🌊 What is this repository?

MacWave itself lives in `MacWaveOrg/MacWave`. This repository carries
**data only** — the installer and `wave selfupdate` never read it, but
`wave install`, `wave search` and `wave info` do, and they read it live
(there is no local cache to refresh).

# 🌊 Layout

```
pkg/pkginfo_{arch}/{name}/_{name}@common             bin_name / des / hom / lic / aut
pkg/pkginfo_{arch}/{name}/_{name}@{version}          url / sha256 / deps

deps/depsinfo_{arch}/{name}/_{name}@common           dep_name / des / hom / lic / aut
deps/depsinfo_{arch}/{name}/_{name}@{version}        url / sha256 / deps
```

`{arch}` is `amd64` (Intel) or `arm64` (Apple Silicon).

- `url` must be `https://`.
- `sha256` is verified before anything is extracted.
- `deps` lists one `name@version` per line, written as a quoted multi-line
  list. A package without a `deps` field has no dependencies.

# 🌊 Automatic Package Updates

The `Package index updates` GitHub Actions workflow checks daily for newer
stable releases and can also be started manually from the Actions tab. For a
safe match, it opens or updates a review pull request instead of publishing
records directly. The PR is assigned to the repository maintainer; merging it
creates a bilingual `Index Update` release in `MacWaveOrg/MacWave`.

The updater currently handles packages whose recorded download URL points to
a public GitHub Release, whose version is plain numeric, and whose current
record has no dependency list. If the homepage is a GitHub repository, it must
match the release repository; otherwise the repository in the existing download
URL is used as the source. The updater recognizes architecture tokens in
release asset filenames (`arm64`/`aarch64` and
`amd64`/`x86_64`/`x86-64`/`x64`), then requires one exact filename-format match
per architecture. It uses GitHub's SHA-256 asset digest, or downloads the
asset to calculate one when GitHub does not provide a digest. Ambiguous assets,
universal binaries, dependency-bearing packages, conda packages, custom mirrors,
and releases with nonstandard version tags are left for manual review.

To enable the automatic release after the PR is merged, create one personal
access token (classic) with the `repo` scope, then add it to this repository as
both the `AUTOMATION_TOKEN` and the `MACWAVE_RELEASE_TOKEN` secret (the same
value under both names). A personal access token
is required because the default `GITHUB_TOKEN` cannot trigger the PR checks or
the post-merge release workflow. The PR author will be the token's account, so
create it under the account that should own the automation PRs. The workflow
fails explicitly if a secret is missing; it does not silently skip publishing.
Automated Index Update releases are always created with `latest=false`.

# 🌊 Install MacWave

In the terminal, run:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/MacWaveOrg/MacWave/HEAD/lib/install.sh)" && source ~/.zshrc
```

(If you are using bash instead of zsh, run `source ~/.bashrc`)

**Requirements: Python (3.14 and above), Xcode Command Line Tools (14.0 and above).**

# 🌊 Supported Packages
(Listed in alphabetical order)

This list is mirrored in `MacWaveOrg/MacWave`'s two READMEs and on [macwave.org](https://macwave.org). See `MacWaveOrg/MacWave/docs/ADD-PACKAGE-CHECKLIST.md` before adding a package.

```
age              by FiloSottile
atuin            by atuinsh
bat              by David Peter
batt             by charlie0129
btop             by Aristocratos
choma            by opa334
cloc             by Al Danial
columbula        by Sha0huaZhang
delta            by dandavison
difft            by Wilfred Hughes
doggo            by mr-karan
duckdb           by duckdb
dust             by bootandy
eza              by Christina Sørensen and the eza community
fd               by David Peter
ffmpeg           by FFmpeg Team
fileicon         by Michael Klement
fx               by antonmedv
fzf              by Junegunn Choi
gh               by cli
gitleaks         by gitleaks
glow             by charmbracelet
gping            by orf
grpcurl          by fullstorydev
htop             by Hisham Muhammad and the htop team
hyperfine        by sharkdp
ipsw             by blacktop
jless            by Paul Julius Martinez
jq               by Stephen Dolan, Nicolas Williams, William Langford, Owen Ou, itchyny, Mattias Wadman, Emanuele Torre, Asaf Meizner, avid Korczynski, et al.
just             by Casey Rodarmor
k9s              by derailed
kubectx          by ahmetb
ldid             by Jay Freeman (saurik) / Procursus Team
lsd              by Abin Simon
mise             by jdx
mkcert           by FiloSottile
ncdu             by Yoran Heling
ollama           by ollama
palera1n         by palera1n Team
pandoc           by John MacFarlane
rclone           by rclone
restic           by restic
rg               by Andrew Gallant
robinsing        by Sha0huaZhang
shellcheck       by koalaman
shfmt            by mvdan
sk               by skim-rs
starship         by starship
stern            by stern
taskwarrior-tui  by kdheepak
tmux             by Nicholas Marriott and contributors
tofu             by opentofu
tree             by Steve Baker, Thomas Moore, Francesc Rocher, Florian Sesser, Kyosuke Tokoro
trollrestore     by JJTech (@JJTech0130)
typst            by typst
vhs              by charmbracelet
websocat         by vi
wget             by GNU Project
xh               by ducaale
yazi             by sxyazi
yq               by Mike Farah
zellij           by zellij-org
zoxide           by Ajeet D'Souza
```

# 🌊 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

# 🌊 Contact Us

Email：[hi@macwave.org](mailto:hi@macwave.org)
