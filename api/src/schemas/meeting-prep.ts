export interface MeetingPrepMeta {
  readonly date: string;
  readonly scores: {
    readonly eeat: {
      readonly experience: number;
      readonly expertise: number;
      readonly authoritativeness: number;
      readonly trustworthiness: number;
    };
    readonly maturity: {
      readonly strategy: string;
      readonly process: string;
      readonly keywords: string;
      readonly metrics: string;
    };
  };
  readonly alert_down_count: number;
  readonly question_count: number;
  readonly generation_mode: string;
}

export interface MeetingPrepSummary {
  readonly date: string;
  readonly filename: string;
  readonly size_bytes: number;
  readonly meta?: MeetingPrepMeta;
}

export interface MaturityDataPoint {
  readonly date: string;
  readonly maturity: {
    readonly strategy: string;
    readonly process: string;
    readonly keywords: string;
    readonly metrics: string;
  };
  readonly eeat: {
    readonly experience: number;
    readonly expertise: number;
    readonly authoritativeness: number;
    readonly trustworthiness: number;
  };
  readonly alert_down_count: number;
}

export interface MaturityTrendSummary {
  readonly improved: readonly string[];
  readonly stagnant: readonly string[];
  readonly regressed: readonly string[];
}

export interface MaturityTrendResponse {
  readonly data_points: readonly MaturityDataPoint[];
  readonly summary: MaturityTrendSummary | null;
  readonly total: number;
}

