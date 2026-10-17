import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getSettings, saveSettings } from "../api/client";
import type { AppSettings } from "../api/types";
import { SettingsView } from "./SettingsView";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, getSettings: vi.fn(), saveSettings: vi.fn() };
});

const mockedGet = vi.mocked(getSettings);
const mockedSave = vi.mocked(saveSettings);

const settings: AppSettings = {
  timezone: "Europe/Moscow",
  reminder_hour: 9,
  reminder_anchor: null,
  new_per_day: 10,
  reviews_per_day: 200,
  desired_retention: 0.9,
  learn_threshold: 3,
};

function renderSettings(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <SettingsView />
    </QueryClientProvider>,
  );
}

describe("SettingsView", () => {
  beforeEach(() => {
    mockedGet.mockReset().mockResolvedValue(settings);
    mockedSave.mockReset();
  });

  it("settings loads and saves", async () => {
    mockedSave.mockImplementation(async (body) => body);
    renderSettings();

    const newPerDay = await screen.findByLabelText("Новых в день");
    expect(newPerDay).toHaveValue(10);
    expect(screen.getByLabelText("Повторений в день")).toHaveValue(200);
    expect(screen.getByLabelText("Целевое удержание")).toHaveValue("0.9");
    expect(screen.getByLabelText("Напоминание (час)")).toHaveValue(9);
    expect(screen.getByLabelText("Привязка")).toHaveValue("");
    expect(screen.getByLabelText("Порог «учить» (0–10)")).toHaveValue(3);
    expect(screen.getByLabelText("Часовой пояс")).toHaveValue("Europe/Moscow");

    fireEvent.change(newPerDay, { target: { value: "15" } });
    fireEvent.change(screen.getByLabelText("Целевое удержание"), { target: { value: "0.88" } });
    fireEvent.change(screen.getByLabelText("Привязка"), { target: { value: "  после кофе " } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(mockedSave).toHaveBeenCalledTimes(1));
    expect(mockedSave.mock.calls[0][0]).toEqual({
      ...settings,
      new_per_day: 15,
      desired_retention: 0.88,
      reminder_anchor: "после кофе",
    });
    expect(await screen.findByText("Сохранено")).toBeInTheDocument();
  });

  it("keeps a stored retention outside the list", async () => {
    mockedGet.mockResolvedValue({ ...settings, desired_retention: 0.97 });
    mockedSave.mockImplementation(async (body) => body);
    renderSettings();

    const retention = await screen.findByLabelText("Целевое удержание");
    expect(retention).toHaveValue("0.97");
    expect(screen.getByRole("option", { name: "97 %" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Новых в день"), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(mockedSave).toHaveBeenCalledTimes(1));
    expect(mockedSave.mock.calls[0][0]).toEqual({ ...settings, desired_retention: 0.97, new_per_day: 7 });
  });

  it("settings shows validation error", async () => {
    mockedSave.mockRejectedValue(new ApiError("Value error, unknown timezone 'Mars/Base'", 422));
    renderSettings();

    fireEvent.click(await screen.findByRole("button", { name: "Сохранить" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Value error, unknown timezone 'Mars/Base'",
    );
    expect(screen.queryByText("Сохранено")).not.toBeInTheDocument();
  });
});
