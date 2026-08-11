import { z } from "zod";

export const recommendationFormSchema = z.object({
  required_flux_lm: z
    .number({ error: "Le flux lumineux est obligatoire." })
    .positive("Le flux lumineux doit etre superieur a 0."),
  max_power_w: z
    .number({ error: "La puissance maximale est obligatoire." })
    .positive("La puissance maximale doit etre superieure a 0."),
  required_cct_k: z
    .number({ error: "La temperature de couleur (CCT) est obligatoire." })
    .positive("La CCT doit etre superieure a 0."),
  voltage_nominal_v: z
    .number({ error: "La tension nominale est obligatoire." })
    .positive("La tension doit etre superieure a 0."),
  current_nominal_ma: z
    .number({ error: "Le courant nominal est obligatoire." })
    .positive("Le courant doit etre superieur a 0."),

  protocol: z.string().optional(),
  led_package: z.string().optional(),
  road_type: z.string().optional(),
  pole_height_m: z.number().positive("La hauteur doit etre positive.").optional(),
  pole_spacing_m: z.number().positive("L'espacement doit etre positif.").optional(),
  ambient_temperature_c: z.number().optional(),

  // Champs additionnels du calculateur technique (jamais envoyes a createRecommendation()) :
  // alimentent uniquement l'apercu POST /api/calculations/preview.
  road_width_m: z.number().positive("La largeur doit etre positive.").optional(),
  road_length_m: z.number().positive("La longueur doit etre positive.").optional(),
  // z.string() (et non z.enum(...)) : le <select> renvoie "" par defaut, que z.enum().optional()
  // rejette (seuls undefined ou une valeur de l'enum sont acceptes) — meme choix que `protocol` ci-dessus.
  layout_type: z.string().optional(),
  operating_hours_per_year: z.number().positive("Les heures doivent etre positives.").optional(),
  energy_price_per_kwh: z.number().positive("Le tarif doit etre positif.").optional(),
});

export type RecommendationFormValues = z.infer<typeof recommendationFormSchema>;

/** Convertit la valeur brute d'un <input type="number"> : chaine vide -> undefined (jamais NaN). */
export function setValueAsNumber(value: string) {
  return value === "" ? undefined : Number(value);
}
