<script lang="ts">
	import { cn } from '$lib/utils';

	let className: string | undefined = undefined;
	export { className as class };
	export let value: string | number = '';
	export let placeholder: string = '';
	export let disabled: boolean = false;

	let inputElement: HTMLInputElement;

	export function focus() {
		inputElement?.focus();
	}
</script>

<input
	bind:this={inputElement}
	{placeholder}
	{disabled}
	bind:value
	class={cn(
		'flex h-10 w-full rounded-lg border-2 border-input bg-background px-3 py-2 text-sm ring-offset-background',
		'file:border-0 file:bg-transparent file:text-sm file:font-medium',
		'placeholder:text-muted-foreground',
		'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-datadog-purple focus-visible:ring-offset-2 focus-visible:border-datadog-purple',
		'disabled:cursor-not-allowed disabled:opacity-50',
		'transition-all duration-200',
		className
	)}
	on:input
	on:change
	on:blur
	on:focus
	{...$$restProps}
/>

