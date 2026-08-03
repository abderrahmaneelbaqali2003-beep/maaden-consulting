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
});

export type RecommendationFormValues = z.infer<typeof recommendationFormSchema>;

/** Convertit la valeur brute d'un <input type="number"> : chaine vide -> undefined (jamais NaN). */
export function setValueAsNumber(value: string) {
  return value === "" ? undefined : Number(value);
}
