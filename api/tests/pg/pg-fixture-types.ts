export interface PgFixtureInfo {
  readonly host: string;
  readonly port: number;
  readonly superUser: string;
  readonly superPassword: string;
  readonly maintenanceDb: string;
  readonly templateDb: string;
  readonly ragUser: string;
  readonly ragPassword: string;
}

declare module "vitest" {
  export interface ProvidedContext {
    pgFixture: PgFixtureInfo | null;
  }
}
