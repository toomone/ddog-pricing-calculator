import ChartContainer from "./chart-container.svelte";
import ChartTooltip from "./chart-tooltip.svelte";
import ChartLegend from "./chart-legend.svelte";

export type ChartConfig = Record<
	string,
	{
		label?: string;
		color?: string;
	}
>;

export { ChartContainer as Container, ChartTooltip as Tooltip, ChartLegend as Legend };

