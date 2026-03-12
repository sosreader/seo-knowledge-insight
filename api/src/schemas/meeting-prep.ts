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


