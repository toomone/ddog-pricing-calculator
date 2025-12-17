import { tv, type VariantProps } from 'tailwind-variants';
import Root from './Badge.svelte';

const badgeVariants = tv({
	base: 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
	variants: {
		variant: {
			default: 'border-transparent bg-datadog-purple text-white',
			secondary: 'border-transparent bg-secondary text-secondary-foreground',
			destructive: 'border-transparent bg-destructive text-destructive-foreground',
			outline: 'text-foreground border-2',
			success: 'border-transparent bg-datadog-green text-white'
		}
	},
	defaultVariants: {
		variant: 'default'
	}
});

type Variant = VariantProps<typeof badgeVariants>['variant'];

export { Root, Root as Badge, badgeVariants, type Variant };

