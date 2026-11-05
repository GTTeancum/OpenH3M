# Battle Canyon placed lights

Status: approved by the user on 2026-11-04: "Approve native H3 placed-light behavior".
Separate from the approved baked-lighting controls.

Keep all 13 original placements: six spot_5, four spot_7 and three omni_1.
Preserve their original attachment models/markers, colors, intensity functions,
maximum reach (20, 1.7 and 2 world units), beam dimensions and Reach projected
light texture. The two invisible anchors already compile with Standoff's
unchanged invisible shader through the standard Blender/JMS/Tool workflow.

Use native H3 light behavior for the source controls H3 does not expose:

- H3's default distance diffusion (0.5), angular smoothness (1), and percent
  spherical (0), instead of inventing equivalents for Reach's separate
  attenuation-start distance and angular hotspot/falloff controls.
- Native H3 shading for the omni light's Reach screenspace-specular option.
- Enable H3's existing allow-shadows-and-gels option on the two spot definitions
  to retain their rectangular beams and original projected texture. Keep shadow
  casting disabled, matching the source's lack of a shadow-casting request.

Light edge softness, falloff and specular highlights may differ. No light is
removed, no replacement lighting algorithm is written, and no brightness tuning
is included. The user reviews actual lighting in MCC before any 360 conversion.

Evidence: official source fields in `work/stock-h3-audit/original-placed-*.light.xml`,
native H3 defaults/schema in `work/stock-h3-audit/h3-placed-light-schema.log`, and
[Microsoft's H3 dynamic-light workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/individual/dynamiclights).
The `.light` attachment/marker workflow and native controls are documented there;
using those defaults for unmatched Reach inputs is the proposed authoring choice,
not a claim of equivalent appearance.
