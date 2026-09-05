# Regenerating the architecture diagrams

Kept out of `AGENTS.md`, which is loaded on every turn and has a byte budget. This is
needed only when a diagram changes, so it costs nothing to look up.

The full standard lives in the user-level steering file `architecture-diagram-standards`.
What follows is only what is specific to this repository, plus the failures that produce a
file which exports *without* the icons — not visible until someone opens the PNG.

## Commands

```bash
make diagrams          # regenerate every .drawio and export SVG + PNG
make diagrams-check    # committed files still match the spec (needs the icon package)
make diagram-assets    # CI-safe: artifacts present, no icons committed, no CJK in EN
```

`make ci` runs `diagram-assets` only, via `drift`. The other two need the AWS Architecture
Icons package and the draw.io desktop app, so they are authoring steps rather than gates.

## Layout

| Artefact | Path |
|---|---|
| Source of truth | `docs/_assets/diagrams/<name>[-en][-dark].drawio` |
| SVG for GitHub | `docs/_assets/images/<name>[-en].svg` |
| PNG for blog posts | `docs/_assets/images/png/<name>[-en][-dark]@2x.png` |

`docs/_assets/` rather than `docs/images/` because the underscore marks the directory as
not-content: this repository's validators walk `docs/**/*.md` and pair `docs/ja/` against
`docs/en/`, and a `-en` suffixed diagram in a content directory confuses that pairing.

There is no dark SVG on purpose. The SVG export carries both themes as CSS `light-dark()`
pairs and the viewer picks, so the light file serves a dark-mode reader too. A PNG cannot
adapt, which is the only reason the dark rasters exist.

Japanese keeps the bare filename. A published blog post links the exported PNG by that
exact path, so renaming it breaks a live image.

## The only method that works for export

Generate the `.drawio` XML directly, with each icon embedded as
`shape=image;image=data:image/svg+xml,<base64>` in the cell's `style` attribute.

Things that do NOT work:

| Approach | Problem |
|---|---|
| draw.io MCP `insert_image_vertex` | Icons render in the editor and disappear on CLI export |
| `mxgraph.aws4.*` service shapes | 2019 icon generation, not the current asset package |
| `data:image/svg+xml;base64,` | draw.io wants the comma-only form; `;base64` exports a blank |
| `xml.sax.saxutils.escape()` on a label | Does not escape `"`. An unescaped quote terminates the attribute and draw.io silently drops that cell **and every cell after it** |

The `mxgraph.aws4.group` *container* shapes are a different thing from the aws4 icon set
and are used: they draw a boundary, not a service mark.

## ONTAP objects have no AWS icon

A Snapshot, a FlexClone, a LUN and a FlexVol are ONTAP mechanisms. The AWS package has
snapshot and volume icons, but they carry the Amazon EBS mark, and putting that mark on an
ONTAP Snapshot says Amazon EBS is doing the work — which is the confusion the FlexClone
figure exists to remove. Name the object in a box instead. Do not substitute another
vendor's mark for a missing icon either; a stand-in attributes the service to whoever's
mark was borrowed.

## Verification is visual

`ET.parse()` passing proves nothing about the picture, and neither does `--check`. Export
the PNG and look at every figure, in each language and each theme separately. Found only
by looking, on the first pass of these two figures: a frame title hidden behind an icon, a
27-character edge label lying across the target's own label, an edge routed straight
through a box it was not connected to, and an icon with no label at all.

`@2x` exports exceed the image read limit. Downscale first:

```bash
sips -Z 1400 docs/_assets/images/png/<name>@2x.png --out /tmp/preview.png
```

## Icon package

Not committed: AWS licenses the assets for use in a diagram, not for redistribution. The
builder resolves it from `--icons`, then `AWS_ICON_PACKAGE`, then the newest
`~/Downloads/Icon-package_*`. The release date is read off the directory name, so a new
quarterly package needs no edit.

A service that shipped recently is absent from an older package. `Arch_AWS-Transform_64.svg`
is in `07312026` and not in `01302026`, so these figures need the newer one.

## ラベルの可読性の下限

`make diagram-fonts` が検査する。数値は `tools/check_diagram_fonts.py` に置いてあり、
規範は `~/.kiro/steering/global-document-readability.md`。

ラベルが表示される大きさは、画像が読者のカラム幅に収まるよう縮小された**後**の大きさで
決まる。したがってキャンバスが広いほど、同じ `fontSize` でも小さく表示される。下限は 2 つで、
両方を満たす必要がある。

| 下限 | 値 | 塞いでいる抜け道 |
|---|---|---|
| 実効サイズ = `fontSize × min(1, 880 / 書き出し幅)` | **14px 以上** | エディタでは読めるが公開ページでは読めないラベル |
| ソースの `fontSize` | **16px 以上** | キャンバスを狭めて実効サイズだけ満たし、文字は小さいまま |

880px は GitHub / dev.to / hatenablog の本文カラム幅。幅は `pageWidth` ではなく書き出した
SVG の幅を使う（draw.io は内容にクロップして `--border` を足すので両者はずれる）。

| キャンバス幅 | 必要な `fontSize` |
|---|---|
| 880px 以下 | 16 |
| 1200px | 20 |
| 1500px | 24 |
| 1600px | 26 |

**キャンバスを広げると必要な font が上がる。** 下限を満たしたまま収まらなくなったときは、
ラベルを 2 行に折る → 補足ボックスを図の外の本文へ出す → キャンバスを 880px 側へ狭めて縦に
積む → 図を分割する → 抽象化する、の順で解決する。**縮小は選択肢に入らない。**

### 既存の負債

`diagram-font-debt.txt` に載っている図は、検査器より前に作られたもので下限を満たしていない。
**このファイルは減る方向にしか動かせない**（未記載の違反も、記載されているのに下限を満たす
ようになったファイルも、どちらも失敗する）。

この 2 図を直すには先に決めることがある。**図内の補足ボックスを記事本文へ移すかどうか。**
移さない場合、下限を満たす font では補足の最長行がキャンバス幅を要求し、キャンバスを広げると
必要な font がさらに上がる。移す場合は図の再レイアウトだけで済む。
