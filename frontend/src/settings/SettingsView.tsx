import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FormEvent } from "react";

import { getSettings, saveSettings } from "../api/client";
import type { AppSettings } from "../api/types";
import { ErrorState, LoadingState } from "../components/PageState";

const RETENTIONS = Array.from({ length: 16 }, (_, i) => (80 + i) / 100);
const FALLBACK_TIME_ZONES = ["UTC", "Europe/Moscow", "Asia/Almaty", "Asia/Novosibirsk"];

function timeZones(current: string): string[] {
  const zones =
    typeof Intl.supportedValuesOf === "function"
      ? Intl.supportedValuesOf("timeZone")
      : FALLBACK_TIME_ZONES;
  return zones.includes(current) ? zones : [current, ...zones];
}

// Like the timezone, a stored value off the 80–95 % list stays selectable, so saving another
// field keeps it.
function retentions(current: number): number[] {
  return RETENTIONS.includes(current) ? RETENTIONS : [...RETENTIONS, current].sort((a, b) => a - b);
}

// Uncontrolled form: native min/max/required guard the obvious, the server validates the rest.
function readForm(form: HTMLFormElement): AppSettings {
  const data = new FormData(form);
  const text = (name: string): string => String(data.get(name) ?? "").trim();
  const num = (name: string): number => Number(text(name));
  return {
    new_per_day: num("new_per_day"),
    reviews_per_day: num("reviews_per_day"),
    desired_retention: num("desired_retention"),
    reminder_hour: num("reminder_hour"),
    reminder_anchor: text("reminder_anchor") || null,
    learn_threshold: num("learn_threshold"),
    timezone: text("timezone"),
  };
}

export function SettingsView(): JSX.Element {
  const queryClient = useQueryClient();
  const { data, error, refetch } = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const save = useMutation({
    mutationFn: (body: AppSettings) => saveSettings(body),
    onSuccess: (saved) => queryClient.setQueryData(["settings"], saved),
  });

  if (error) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }
  if (!data) {
    return <LoadingState title="Настройки" message="Загружаем настройки…" />;
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    save.mutate(readForm(event.currentTarget));
  };

  return (
    // Remount when the device timezone sync updates the stored zone (uncontrolled form).
    <form key={data.timezone} className="surface-panel settings-form" onSubmit={onSubmit}>
      <h2>Настройки</h2>
      <label>
        Новых в день
        <input name="new_per_day" type="number" min={0} max={100} required defaultValue={data.new_per_day} />
      </label>
      <label>
        Повторений в день
        <input
          name="reviews_per_day"
          type="number"
          min={0}
          max={1000}
          required
          defaultValue={data.reviews_per_day}
        />
      </label>
      <label>
        Целевое удержание
        <select name="desired_retention" defaultValue={String(data.desired_retention)}>
          {retentions(data.desired_retention).map((retention) => (
            <option key={retention} value={retention}>
              {Math.round(retention * 1000) / 10} %
            </option>
          ))}
        </select>
      </label>
      <label>
        Напоминание (час)
        <input name="reminder_hour" type="number" min={0} max={23} required defaultValue={data.reminder_hour} />
      </label>
      <label>
        Привязка
        <input
          name="reminder_anchor"
          type="text"
          maxLength={255}
          placeholder="Необязательно"
          defaultValue={data.reminder_anchor ?? ""}
        />
      </label>
      <label>
        Порог «учить» (0–10)
        <input name="learn_threshold" type="number" min={0} max={10} required defaultValue={data.learn_threshold} />
      </label>
      <label>
        Часовой пояс
        <select name="timezone" defaultValue={data.timezone} aria-describedby="timezone-hint">
          {timeZones(data.timezone).map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
      </label>
      <span id="timezone-hint" className="field-hint">
        Определяется по устройству при каждом открытии
      </span>

      {save.error ? (
        <p className="batch-message-error" role="alert">
          {save.error.message}
        </p>
      ) : null}
      {save.isSuccess ? (
        <p className="section-label" role="status">
          Сохранено
        </p>
      ) : null}

      <button type="submit" className="primary-button" disabled={save.isPending}>
        Сохранить
      </button>
    </form>
  );
}
