import { describe, expect, it } from "vitest";
import { extractBlobErrorMessage, extractErrorMessage } from "./client";

function fakeAxiosError(overrides: Record<string, unknown>) {
  return { isAxiosError: true, ...overrides };
}

describe("extractErrorMessage", () => {
  it("lit le detail JSON standard", () => {
    const err = fakeAxiosError({ response: { status: 409, data: { detail: "Conflit." } } });
    expect(extractErrorMessage(err)).toBe("Conflit.");
  });

  it("indique que le serveur est injoignable en l'absence de reponse", () => {
    const err = fakeAxiosError({ response: undefined });
    expect(extractErrorMessage(err)).toMatch(/Impossible de contacter le serveur/);
  });
});

describe("extractBlobErrorMessage", () => {
  it("relit un blob d'erreur JSON et extrait le detail (409 configuration non validee)", async () => {
    const blob = new Blob(
      [JSON.stringify({ detail: "La configuration doit etre validee avant la generation du rapport final." })],
      { type: "application/json" }
    );
    const err = fakeAxiosError({ response: { status: 409, data: blob } });

    const message = await extractBlobErrorMessage(err, "fallback");

    expect(message).toBe("La configuration doit etre validee avant la generation du rapport final.");
  });

  it("relit un blob d'erreur JSON 500 et extrait le detail", async () => {
    const blob = new Blob([JSON.stringify({ detail: "Impossible de generer le rapport PDF." })], {
      type: "application/json",
    });
    const err = fakeAxiosError({ response: { status: 500, data: blob } });

    const message = await extractBlobErrorMessage(err, "fallback");

    expect(message).toBe("Impossible de generer le rapport PDF.");
  });

  it("retombe sur le message par defaut si le blob n'est pas un JSON exploitable", async () => {
    const blob = new Blob(["<html>not json</html>"], { type: "text/html" });
    const err = fakeAxiosError({ response: { status: 502, data: blob } });

    const message = await extractBlobErrorMessage(err, "Impossible de telecharger le rapport PDF.");

    expect(message).toBe("<html>not json</html>");
  });

  it("signale un serveur injoignable (erreur reseau, pas de reponse)", async () => {
    const err = fakeAxiosError({ response: undefined });

    const message = await extractBlobErrorMessage(err, "fallback");

    expect(message).toMatch(/Impossible de contacter le serveur/);
  });

  it("utilise le message de repli pour une erreur non-Axios", async () => {
    const message = await extractBlobErrorMessage(new Error("boom"), "Impossible de telecharger le rapport PDF.");
    expect(message).toBe("Impossible de telecharger le rapport PDF.");
  });
});
