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
pkg/pkginfo_{arch}/{name}/_{name}@{version}          url / sha256 / file / [install] / deps

deps/depsinfo_{arch}/{name}/_{name}@common           dep_name / des / hom / lic / aut
deps/depsinfo_{arch}/{name}/_{name}@{version}        url / sha256 / deps
```

`{arch}` is `amd64` (Intel) or `arm64` (Apple Silicon).

- `url` must be `https://`.
- `sha256` is verified before anything is extracted.
- `deps` lists one `name@version` per line, written as a quoted multi-line
  list. A package without a `deps` field has no dependencies.
- `install` is optional and only appears on version records:

  | value | meaning |
  | --- | --- |
  | *(absent)* or `"binary"` | the payload holds one executable; it is installed as `bin/{name}@{version}/{name}` |
  | `"tree"` | the payload is a whole directory tree (for example `bin/`, `libexec/`, `share/`); it is installed as `bin/{name}@{version}/` and only `bin/{name}` is linked |

  A missing `install` field means a normal single-executable package, so every
  record written before this field existed keeps working unchanged. `tree` is
  meant for packages upstream cannot ship as one file — `git` is the first one.

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

7zz              by Igor Pavlov
act              by nektos
actionlint       by rhysd
age              by FiloSottile
aria2c           by Tatsuhiro Tsujikawa
ast-grep         by ast-grep
atuin            by atuinsh
bat              by David Peter
batt             by charlie0129
btm              by Clement Tsang
btop             by Aristocratos
chezmoi          by twpayne
choma            by opa334
circleci         by CircleCI
cloc             by Al Danial
cloudflared      by cloudflare
columbula        by Sha0huaZhang
cosign           by Sigstore
delta            by dandavison
difft            by Wilfred Hughes
direnv           by direnv
docker-compose   by Docker
doggo            by mr-karan
dtc              by Device Tree Compiler contributors
duckdb           by duckdb
dust             by bootandy
eza              by Christina Sørensen and the eza community
fd               by David Peter
ffmpeg           by FFmpeg Team
fileicon         by Michael Klement
fish             by fish-shell contributors
flyctl           by superfly
fx               by antonmedv
fzf              by Junegunn Choi
gbash            by Free Software Foundation
gh               by cli
git              by Git community
git-lfs          by git-lfs
gitleaks         by gitleaks
glow             by charmbracelet
golangci-lint    by golangci
gpatch           by Free Software Foundation
gping            by orf
grpcurl          by fullstorydev
gtar             by Free Software Foundation
gwget            by GNU Project
hadolint         by Hadolint
helm             by helm
htop             by Hisham Muhammad and the htop team
hx               by Helix contributors
hyperfine        by sharkdp
ipsw             by blacktop
jj               by Jujutsu contributors
jless            by Paul Julius Martinez
jq               by Stephen Dolan, Nicolas Williams, et al.
just             by Casey Rodarmor
k9s              by derailed
kind             by Kubernetes SIG Testing
kubecolor        by kubecolor
kubeconform      by yannh
kubectx          by ahmetb
kustomize        by Kubernetes SIG CLI
lazydocker       by Jesse Duffield
lazygit          by jesseduffield
ldid             by Jay Freeman (saurik) / Procursus Team
lefthook         by Evil Martians
lsd              by Abin Simon
macmon           by Vlad Kens
mint             by Yonas Kolb
mise             by jdx
mkcert           by FiloSottile
ncdu             by Yoran Heling
nu               by Nushell contributors
nvim             by neovim
ollama           by ollama
palera1n         by palera1n Team
pandoc           by John MacFarlane
rclone           by rclone
restic           by restic
rg               by Andrew Gallant
robinsing        by Sha0huaZhang
ruff             by astral-sh
scc              by Ben Boyter
shellcheck       by koalaman
shfmt            by mvdan
sk               by skim-rs
sops             by getsops
spf              by yorukot
starship         by starship
stern            by stern
syncthing        by Syncthing contributors
taskwarrior-tui  by kdheepak
tectonic         by Tectonic contributors
testdisk         by Christophe Grenier
tldr             by tealdeer-rs
tmux             by Nicholas Marriott and contributors
tofu             by opentofu
tree             by Steve Baker, Thomas Moore, et al.
trivy            by aquasecurity
trollrestore     by JJTech (@JJTech0130)
ty               by Astral
typst            by typst
uv               by astral-sh
vhs              by charmbracelet
watchexec        by Watchexec contributors
websocat         by vi
xcbeautify       by cpisciotta
xclogparser      by MobileNativeFoundation
xcodegen         by Yonas Kolb
xh               by ducaale
yazi             by sxyazi
yq               by Mike Farah
yt-dlp           by yt-dlp
zellij           by zellij-org
zoxide           by Ajeet D'Souza
```

# 🌊 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

# 🌊 Contact Us

Email：[hi@macwave.org](mailto:hi@macwave.org)
