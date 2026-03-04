import path from "path";

/** @type {import('next').NextConfig} */
const nextConfig = {
	webpack: (config, { dev }) => {
		config.resolve.alias = {
			...(config.resolve.alias ?? {}),
			"@": path.resolve(process.cwd())
		};

		if (dev) {
			config.cache = false;
		}
		return config;
	}
};

export default nextConfig;
